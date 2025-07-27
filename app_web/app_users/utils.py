import logging

import stripe
import requests
from firebase_admin import auth as fb_auth
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from app_users.models import CustomUser, UserGeneratedToken
from app_users.forms import CustomUserCreationForm
from app_users.tokens import generate_email_verification_token
from app_users.tasks import (
    send_user_welcome_email_message, send_user_validation_email
)
from app_settings.utils import get_setting
from app_financial.models import StripeSubscriptionItem, CustomerCreditsBought
from app_financial.utils import soft_delete_user_subscription_item
from common.redis_logic.redis_schemas import (
    REDIS_KEY_USER_GENERATED_TOKEN,
    REDIS_KEY_USER_CREDIT_BOUGHT,
    REDIS_KEY_USER_API_DAILY_CALL_LIMIT,
    REDIS_KEY_METERED_SUBSCRIPTION_USERS,
    REDIS_KEY_USER_DJANGO_CALL_RATE_LIMIT,
    REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION,
    REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
    REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER,
    REDIS_KEY_USER_PHONE_NUMBER
)
from common.redis_logic.custom_redis import (
    set_redis_key, delete_redis_key, rename_redis_key,
)
from common.redis_logic.redis_utils import add_one_time_credits_to_customer
from common.exceptions import CustomValidationError, CustomRequestException
from common.normalize import get_normalized_email
from common.other import generate_random_string
from common.auth import validate_password


logger = logging.getLogger(__name__)


def get_users_with_normalized_email(normalized_email: str):
    return CustomUser.objects.filter(normalized_email=normalized_email)


def create_user(
    email: str,
    password1: str,
    password2: str,
    email_verified: bool = False,
) -> tuple[CustomUser, bool]:
    """
    Returns a tuple with the user object and a boolean indicating if the user
    was created or not.
    """

    validate_password(password1, password2)

    try:
        validate_email(email)
    except ValidationError:
        CustomValidationError(dict_errors={"email": "Email format is not valid."})

    try:
        form = CustomUserCreationForm(
            data={
                "username": generate_random_string(),  # temporary
                "email": email,
                "password1": password1,
                "password2": password2,
                "stripe_customer_id": f"temp_customer_{generate_random_string()}",
            }
        )

        if form.is_valid():
            user_obj, created = form.save()
            if created:
                fb_user_obj = fb_auth.create_user(
                    email=email,
                    email_verified=email_verified,
                    password=password1,
                )
                user_obj.username = fb_user_obj.uid

                stripe_customer = stripe.Customer.create(
                    email=email,
                    description=f"Customer for - {email}",
                )

                user_obj.stripe_customer_id = stripe_customer.id
                # because we are verifying the email with Firebase
                user_obj.is_active = True
                user_obj.save()

                send_user_validation_email.delay(
                    user_email=email,
                    token=generate_email_verification_token(user_pk=user_obj.pk)
                )

                # here we add the default Limit for Daily API calls
                set_redis_key(
                    REDIS_KEY_USER_API_DAILY_CALL_LIMIT.format(
                        username=user_obj.username
                    ),
                    simple_value=user_obj.api_daily_call_limit,
                )

            return user_obj, created
        else:
            raise CustomValidationError(dict_errors=form.errors)
    except ValueError:
        raise CustomValidationError(msg_error="Email or password are not valid.")
    except fb_auth.EmailAlreadyExistsError:
        logging.error(
            f"Email already exists {email}. This might happen if the "
            "user has an account but is not logged in when trying to "
            "subscribe."
        )
        raise CustomValidationError(msg_error="Email already exists.")
    except ObjectDoesNotExist:
        raise CustomValidationError(
            msg_error="There was an error creating your account."
        )
    except CustomRequestException as e:
        raise CustomValidationError(msg_error=str(e))


def deactivate_anonymize_user(user_obj: CustomUser) -> tuple[CustomUser, bool]:
    """
    Soft delete user.
    Anonymize user data. This is used when a user deletes their account.

    We do not normalize the email here because we want to keep the original
    so that we don't give the same credits to the same email address.
    """
    success = False
    try:
        random_username = generate_random_string()
        random_email = random_username + "@doodleops.com"
        fb_auth.delete_user(uid=user_obj.username)
        user_obj.username = random_username
        user_obj.email = random_email
        user_obj.is_active = False
        user_obj.save()
        success = True
    except fb_auth.UserNotFoundError:
        logger.error(f"User not found {user_obj.username} - {user_obj.email}")
    except fb_auth.FirebaseError as e:
        logger.error(f"Error updating Stripe user {user_obj.username} - {e}")
    except Exception as e:
        logger.error(
            f"Unknown Error updating Stripe user {user_obj.username} - {e}"
        )
    finally:
        return user_obj, success


def delete_user_and_connected_data(
    user_obj: CustomUser,
    subs_item_obj: StripeSubscriptionItem | None = None,
) -> bool:
    """
    Soft delete user.
    This is used when a user deletes their account.
    """
    for token_obj in UserGeneratedToken.objects.filter(user=user_obj):
        token_value = token_obj.token
        token_obj.delete()
        redis_key = REDIS_KEY_USER_GENERATED_TOKEN.format(
            token=token_value, username=user_obj.username
        )
        delete_redis_key(key=redis_key)

    if subs_item_obj:
        try:
            stripe.SubscriptionItem.delete(subs_item_obj.id)
        except (
            stripe.error.InvalidRequestError,
            stripe.error.AuthenticationError,
            stripe.error.APIConnectionError,
            stripe.error.StripeError,
            Exception,
        ) as e:
            logger.error(
                "Error deleting Subscription Item "
                f"{subs_item_obj.subscription_id} - {e}"
            )
            raise CustomRequestException(
                (
                    "There was an error deleting your account. Please "
                    "contact support."
                ),
                http_status_code=500,
            )

        # SQL / Redis soft delete
        soft_delete_user_subscription_item(
            user_obj=user_obj, subscription_item_id=subs_item_obj.subscription_id
        )

    stripe_subs = stripe.Subscription.list(customer=user_obj.stripe_customer_id)

    if not subs_item_obj and stripe_subs:
        logger.error(
            f"User {user_obj.username} has Stripe subscriptions but no "
            "Subscription Item object."
        )
        for sub in stripe_subs.data:
            try:
                stripe.Subscription.delete(sub.id)
            except (
                stripe.error.InvalidRequestError,
                stripe.error.AuthenticationError,
                stripe.error.APIConnectionError,
                stripe.error.StripeError,
                Exception,
            ) as e:
                logger.error(
                    "Error deleting Subscription Item " f"{sub.id} - {e}"
                )
                raise CustomRequestException(
                    "There was an error deleting your account.",
                    http_status_code=500,
                )


    stripe_customer_id = user_obj.stripe_customer_id
    # anonymize user data
    anon_user_obj, success = deactivate_anonymize_user(user_obj=user_obj)

    # Redis hard delete
    for k in (
        REDIS_KEY_USER_API_DAILY_CALL_LIMIT,
        REDIS_KEY_METERED_SUBSCRIPTION_USERS,
        REDIS_KEY_USER_DJANGO_CALL_RATE_LIMIT,
        REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION,
        REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
    ):
        delete_redis_key(key=k.format(username=user_obj.username))

    if user_obj.phone_number.number:
        delete_redis_key(
            REDIS_KEY_USER_PHONE_NUMBER.format(
                number=user_obj.phone_number.number
            )
        )

    rename_redis_key(
        template_key=REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.format(
            date="*", username="{old_value}", api_name="*", timestamp="*",
            random_char="*"
        ),
        old_value=user_obj.username,
        new_value=anon_user_obj.username
    )

    for cred_bought_obj in CustomerCreditsBought.objects.filter(user=user_obj):
        delete_redis_key(
            key=REDIS_KEY_USER_CREDIT_BOUGHT.format(
                username=cred_bought_obj.user.username,
                id=cred_bought_obj.id,
            )
        )
        cred_bought_obj.delete()
    # we remove the all payment methods from Stripe
    try:
        payment_methods = stripe.PaymentMethod.list(customer=stripe_customer_id)
        for pm in payment_methods.data:
            stripe.PaymentMethod.detach(pm.id)

        if success:
            stripe.Customer.modify(
                stripe_customer_id,
                name=anon_user_obj.username,
                email=anon_user_obj.email,
                address={
                    "city": "",
                    "country": "",
                    "line1": "",
                    "line2": "",
                    "postal_code": "",
                    "state": "",
                },
                phone=None,
                description="",
            )
            return True
    except (
        stripe.error.InvalidRequestError,
        stripe.error.AuthenticationError,
        stripe.error.APIConnectionError,
        stripe.error.StripeError,
        Exception,
    ) as e:
        logger.error(
            "Error deleting Payment Methods " f"{stripe_customer_id} - {e}"
        )
        raise CustomRequestException(
            "There was an error deleting your account.",
            http_status_code=500,
        )

    return False


def exchange_google_token_for_firebase_id_token(google_id_token):
    response = requests.post(
        url=settings.FB_SIGNIN_WITH_IDP_URL,
        json={
            "postBody": f"id_token={google_id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnIdpCredential": True,
            "returnSecureToken": True
        },
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        return response.json().get('idToken')
    else:
        logger.error(f"Error exchanging token: {response.text}")
        raise Exception(f"Error exchanging token: {response.text}")


def get_new_user_credit_message(user_obj: CustomUser, is_sso: bool = False) -> str:
    """
    If this is a completely new user, we also give them credits.
    """
    users = get_users_with_normalized_email(get_normalized_email(user_obj.email))

    if users.count() == 1:
        amount_in_cents = get_setting(
            key="credits_per_user_signup_in_cents",
            default=20,
            expected_type=int,
        )
        no_of_credits = add_one_time_credits_to_customer(
            user_obj=user_obj, amount_in_cents=amount_in_cents,
            details="Initial credits for new user."
        )

        msg = (
            f"Account created for {user_obj.email}! You have been given "
            f"{no_of_credits} credits to get started."
        )
        send_user_welcome_email_message(
            to_email=user_obj.email, credits=no_of_credits
        )
    else:
        msg = f"Account created for {user_obj.email}!"
        send_user_welcome_email_message.delay(to_email=user_obj.email)

    if not is_sso:  # Simple Sign On (like Google does not need this)
        msg += " Please verify your email address."

    return msg
