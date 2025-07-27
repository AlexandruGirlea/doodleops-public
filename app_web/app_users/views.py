import json
import time
import uuid
import random
import string
import logging
from urllib.parse import urlencode

import stripe
import requests
from firebase_admin import auth as fb_auth
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import update_session_auth_hash
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import login as auth_login
from django.core.exceptions import (
    ValidationError,
    PermissionDenied,
    ObjectDoesNotExist,
    MultipleObjectsReturned,
)

from app_settings.utils import get_setting
from app_users.models import (
    CustomUser, UserGeneratedToken, AccountCreationIP, PasswordResetToken,
    PhoneNumbers
)
from app_users.utils import (
    create_user, delete_user_and_connected_data,
    exchange_google_token_for_firebase_id_token, get_new_user_credit_message
)
from app_users.forms import (
    TokenDescriptionForm, ProfileSecurityForm, SetNewPasswordForm
)
from app_users.tasks import (
    send_user_delete_email_message, send_user_reset_password_email,
    send_user_sms_to_validate_phone_number
)
from app_users.tokens import verify_email_token, generate_email_verification_token
from app_api.models import APICounter, API, APIApp
from app_financial.models import (
    StripeSubscriptionItem, StripeInvoice, CustomerCreditsBought
)
from common.exceptions import CustomValidationError, CustomRequestException
from common.auth import validate_password
from common.firebase import (
    get_jwt_token as fb_get_jwt_token,
    delete_user_based_on_credentials as fb_delete_user_based_on_credentials,
    update_user_password as fb_update_user_password,
)
from common.stripe_logic.stripe_utils import get_stripe_customer_portal_url
from common.redis_logic.redis_utils import (
    get_remaining_credits_bought,
    get_remaining_monthly_subscription_credits,
    get_user_api_usage_for_current_day,
    get_instant_cost_in_dollars_for_metered_subscription,
)
from common.redis_logic.custom_redis import set_redis_key, delete_redis_key
from common.redis_logic.redis_schemas import (
    REDIS_KEY_USER_API_DAILY_CALL_LIMIT, REDIS_KEY_USER_PHONE_NUMBER
)
from common.date_time_utils import (
    get_date_time_for_one_year_back, get_current_date_time,
    get_date_time_for_specified_hours_ago
)
from common.normalize import get_normalized_email
from common.other import get_client_ip, generate_random_string
from common.recaptcha_logic import validate_recaptcha


logger = logging.getLogger(__name__)

NUMBER_OF_PHONE_NUMBER_VERIFICATION_ATTEMPTS = 5


def create_account(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method.upper() != "POST":
        return render(
            request=request,
            template_name="create_account.html",
            context={"recaptcha_public_key": settings.RECAPTCHA_PUBLIC_KEY,}
            )

    try:
        validate_recaptcha(request)
    except ValidationError as e:
        messages.error(request, e.message)
        return redirect('create_account')

    client_ip = get_client_ip(request)
    if client_ip:
        ip_record, created = AccountCreationIP.objects.get_or_create(
            ip_address=client_ip
        )

        if ip_record.is_rate_limited():
            messages.error(
                request,
                'Too many account creation attempts. Please wait 24 hours before '
                'trying again.',
            )
            return redirect('login')

    password1 = request.POST.get("password1")
    password2 = request.POST.get("password2")
    email = request.POST.get("email", "").lower()

    if not all([password1, password2, email]):
        messages.error(request, "Please fill all fields")
        return redirect("create_account")

    if CustomUser.objects.filter(email=email).exists():
        messages.error(request, "Email already exists")
        return redirect("create_account")

    try:
        user_obj, created = create_user(
            email=email,
            password1=password1,
            password2=password2,
        )
        if user_obj and created:
            msg = get_new_user_credit_message(user_obj)

            messages.success(request, msg)
            return redirect("login")
        else:
            messages.error(request, "There was an error creating your account.")
            return redirect("create_account")
    except CustomValidationError as e:
        fb_delete_user_based_on_credentials(email, password1)
        user_obj = CustomUser.objects.filter(email=email).first()
        if user_obj and "temp" not in user_obj.stripe_customer_id:
            stripe.Customer.delete(user_obj.stripe_customer_id)
        user_obj.delete()

        if e.msg_error:
            messages.error(request, e.msg_error)
            return redirect("create_account")
        return render(request, "create_account.html", {"errors": e.dict_errors})


def login(request):
    if request.user.is_authenticated:
        logger.info(f"User {request.user.username} is already logged in.")
        if request.GET.get('next'):
            return redirect(request.GET.get('next'))
        return redirect("index")
    elif request.method.upper() != "POST":
        list_of_allowed_oauth_redirects = [
            "o/authorize/"
            "o/token/"
            "o/revoke_token/"
            "o/introspect/"
            "o/applications/"
        ]
        
        if request.GET.get('next'):
            if any(
                [url in request.GET.get('next')
                 for url in list_of_allowed_oauth_redirects]
            ):
                request.session['oauth_next'] = request.GET.get('next')
        return render(
            request=request,
            template_name="login.html",
            context={"recaptcha_public_key": settings.RECAPTCHA_PUBLIC_KEY, }
        )

    try:
        validate_recaptcha(request)
    except ValidationError as e:
        messages.error(request, e.message)
        return redirect('login')

    email = request.POST.get("email", "").lower()
    password = request.POST.get("password", "")

    try:
        jwt_token, refresh_token = fb_get_jwt_token(email, password)
    except PermissionDenied:
        msg = f"Email or password are not valid for {email}"
        logger.error(msg)
        messages.error(request, msg)
        return redirect("login")

    try:
        payload = fb_auth.verify_id_token(jwt_token)
        if payload.get("email") != email or payload.get("exp") < int(time.time()):
            logger.error("Payload Email or exp is not valid")
            raise PermissionDenied()
        if not payload.get("email_verified"):
            msg = "Email not verified"
            logger.error(msg)
            messages.error(request, msg)
            return redirect("login")

        user_obj = CustomUser.objects.get(
            username=payload.get("user_id"),
            email=email,
        )
        if not user_obj.is_active:
            msg = "Account is not active"
            logger.error(msg)
            messages.error(request, msg)
            return redirect("login")

        auth_login(request, user_obj)  # this sets `request.user`
        request.session["username"] = payload.get("user_id")
        request.session["email"] = email

        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url, allowed_hosts=request.get_host()
        ):
            return HttpResponseRedirect(next_url)
        return redirect("index")
    except (
        ValueError,
        fb_auth.ExpiredIdTokenError,
        ObjectDoesNotExist,
        fb_auth.InvalidIdTokenError,
        fb_auth.RevokedIdTokenError,
    ) as e:
        logger.error(f"Error: {str(e)}")
        msg = f"Email or password are not valid for {email}"
        messages.error(request, msg)
        return redirect("login")


def logout(request):
    auth_logout(request)
    messages.success(request, f"You have been logged out.")
    return redirect("login")


def forgot_password(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method.upper() != "POST":
        return render(
            request=request,
            template_name="forgot_password.html",
            context={"recaptcha_public_key": settings.RECAPTCHA_PUBLIC_KEY, }
        )

    try:
        validate_recaptcha(request)
    except ValidationError as e:
        messages.error(request, e.message)
        return redirect('forgot_password')
    except Exception as e:
        logger.error(f"Error: {e}")
        messages.error(request, "An error occurred. Please try again later.")
        return redirect('forgot_password')

    email = request.POST.get("email", "").lower()

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Email format is not valid.")
        return redirect('forgot_password')

    try:
        user_obj = CustomUser.objects.get(email=email)
        if user_obj:
            token = generate_email_verification_token(user_pk=user_obj.pk)
            send_user_reset_password_email.delay(
                user_email=email, token=token
            )
    # except object does not exist
    except (
            ObjectDoesNotExist, fb_auth.UserNotFoundError,
            CustomRequestException
    ) as e:
        logger.warning(f"Forgot password - Email not found, Error: {str(e)}")

    messages.success(request, f"A password reset email has been sent to {email} "
                              f"if an account with that email exists.")
    return redirect("login")


@login_required
def profile_general(request):
    if request.method != "GET" or not request.user.is_authenticated:
        raise Http404

    username = request.user.username
    remaining_credits_bought_dict = get_remaining_credits_bought(username)
    context = {
        "remaining_credits_bought": sum(remaining_credits_bought_dict.values()),
        "remaining_monthly_subscription_credits": (
            get_remaining_monthly_subscription_credits(username)
        ),
    }
    context["total_credits"] = sum(context.values())

    if context["remaining_credits_bought"]:
        remaining_credits_bought_obj = (
            CustomerCreditsBought.objects.filter(
                pk__in=remaining_credits_bought_dict.keys()
            ).order_by("-pk")
        )
        remaining_credits_bought_details = {}
        for obj in remaining_credits_bought_obj:
            remaining_credits_bought_details[obj.id] = {
                "credits_bought": obj.credits,
                "credits_remaining": remaining_credits_bought_dict[obj.id],
                "created": obj.created,
                "expires": obj.expires,
            }

        context["remaining_credits_bought_details"] = (
            remaining_credits_bought_details
        )

    try:
        stripe_subs_item = StripeSubscriptionItem.objects.get(
            user=request.user,
            is_active=True,
            is_deleted=False,
        )
    except ObjectDoesNotExist:
        stripe_subs_item = None
    except MultipleObjectsReturned:
        logger.error(
            "Multiple StripeSubscriptionItem objects found for user "
            f"{request.user.username}."
        )
        raise Http404

    context["stripe_customer_portal_url"] = request.build_absolute_uri(
        reverse("stripe_customer_portal")
    )

    if stripe_subs_item:
        context["pricing_plan_name"] = str(stripe_subs_item.pricing_plan)

        if stripe_subs_item.pricing_plan.is_metered:
            context["user_metered_cost_for_current_month_url"] = (
                reverse("get_instant_cost_for_metered_subscription")
                + f"?subscription_item_id={stripe_subs_item.id}"
            )
            context["subscription_name"] = stripe_subs_item.pricing_plan.name
        else:
            context["pricing_plan_name"] += (
                f" ({stripe_subs_item.pricing_plan.price_in_cents / 100}$)"
            )
    return render(request, "profile_general.html", context)


@login_required
def get_instant_cost_for_metered_subscription(request):
    if request.method != "GET" or not request.user.is_authenticated:
        raise Http404

    try:
        subs_item_obj = StripeSubscriptionItem.objects.get(
            id=request.GET.get("subscription_item_id"),
            user=request.user,
        )
    except ObjectDoesNotExist:
        raise Http404

    return JsonResponse(
        {
            "user_instant_cost_in_dollars_for_metered_subscription": (
                get_instant_cost_in_dollars_for_metered_subscription(
                    subs_item_obj=subs_item_obj,
                )
            )
        }
    )


@login_required
def redirect_to_stripe_customer_portal_url(request):
    """
    This needs to get created on user request, not on page load.
    For faster load times of user profile page and because the Stripe link
    expires after a few minutes.

    All users should have a stripe_customer_id, even if they don't have a
    subscription => they can still mange their payment method and see their
    invoices.
    """
    if request.method != "GET" or not request.user.is_authenticated:
        raise Http404

    return redirect(
        get_stripe_customer_portal_url(
            customer_id=request.user.stripe_customer_id,
            return_url=request.build_absolute_uri(
                reverse("profile_general")
            ),
        )
    )


@login_required
def profile_security(request):
    if not request.user.is_authenticated:
        raise Http404

    elif request.method.upper() == "GET":
        return render(request, "profile_security.html")

    elif request.method.upper() == "POST":
        user_obj = request.user

        form = ProfileSecurityForm(request.POST)

        if not form.is_valid():
            messages.error(request, form.errors)
            return redirect("profile_security")

        password = form.cleaned_data.get("password")

        password1 = form.cleaned_data.get("password1")
        password2 = form.cleaned_data.get("password2")

        if not all([password1, password2]):
            messages.error(request, "Please fill all fields")
            return redirect("profile_security")

        if not request.user.is_active:
            messages.error(request, "Your account is not active")
            return redirect("profile_security")

        try:
            validate_password(password1=password1, password2=password2)
        except CustomValidationError as e:
            return render(
                request, "profile_security.html", {"errors": e.dict_errors}
            )

        if not user_obj.has_usable_password():
            user_obj.set_password(password1)
            user_obj.save()
            update_session_auth_hash(request, user_obj)

            fb_user = fb_auth.get_user_by_email(user_obj.email)
            fb_auth.update_user(fb_user.uid, password=password1)

            messages.success(request, "Password updated successfully")
            return render(request, "profile_security.html")

        elif user_obj.has_usable_password() and password:
            if not all([password, password1, password2]):
                messages.error(request, "Please fill all fields")
                return redirect("profile_security")

            try:
                if fb_update_user_password(
                    user_obj=request.user,
                    password=password,
                    new_password1=password1,
                    new_password2=password2,
                ):
                    user_obj.set_password(password1)
                    user_obj.save()
                    update_session_auth_hash(request, user_obj)
                    messages.success(request, "Password updated successfully")

                else:
                    messages.error(
                        request,
                        "Password not updated. Unknown error, please contact "
                        "support.",
                    )

                return redirect("profile_security")

            except CustomValidationError as e:
                if e.msg_error:
                    messages.error(request, e.msg_error)
                    return redirect("profile_security")
                return render(
                    request, "profile_security.html", {"errors": e.dict_errors}
                )
            except CustomRequestException as e:
                messages.error(request, str(e))
                return redirect("profile_security")
            except ValueError as e:
                messages.error(request, str(e))
                return redirect("profile_security")

        messages.error(request, form.errors)
    return redirect("profile_security")


@login_required
def profile_api_usage(request):
    if request.method != "GET" or not request.user.is_authenticated:
        raise Http404

    api_apps = APIApp.objects.all()

    api_names = {
        api.html_template_path.replace(".html", ""): {
            "url_path": api.url_path,
            "display_name": api.display_name,
            "api_app_url_path": api_apps.get(id=api.api_app_id).url_path,
        }
        for api in API.objects.all()
    }

    db_object_list = list(
        APICounter.objects.filter(
            username=request.user.username,
            date__gte=get_date_time_for_one_year_back(get_date=True),
            date__lt=get_current_date_time(get_date=True),
        ).order_by("-date")
    )
    redis_api_counter_objs = get_user_api_usage_for_current_day(
        username=request.user.username
    )
    paginator = Paginator(redis_api_counter_objs + db_object_list, 10)

    page_number = request.GET.get("page")

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    if not page_obj.object_list and page_number != "1":
        return redirect(request.path + "?page=1")

    for obj in page_obj.object_list:
        if api_names.get(obj.api_name):
            obj.api_url = api_names.get(obj.api_name).get("url_path")
            obj.api_app_url_path = api_names.get(obj.api_name).get(
                "api_app_url_path"
            )

        obj.api_name = api_names.get(
            obj.api_name, {"display_name": obj.api_name}
        ).get("display_name")

    return render(request, "profile_api_usage.html", {"page_obj": page_obj})


@login_required
def profile_api_keys(request):
    if (
        request.method.upper() not in ["GET", "POST"]
        or not request.user.is_authenticated
    ):
        raise Http404

    subscription_item = StripeSubscriptionItem.objects.filter(
        user=request.user,
        is_active=True,
        is_deleted=False,
    ).first()

    pricing_plan = subscription_item.pricing_plan if subscription_item else None

    if not pricing_plan or not pricing_plan.is_metered:
        return render(
            request, "profile_api_keys.html",
            context={
                "not_metered": (
                    "You need to have an active Enterprise subscription "
                    "to generate API keys."
                )
            }
        )

    context = {
        "api_keys": UserGeneratedToken.objects.filter(user=request.user).order_by(
            "-created_at"
        )
    }
    if request.method.upper() == "GET":
        return render(request, "profile_api_keys.html", context)

    elif request.method.upper() == "POST":
        form = TokenDescriptionForm(request.POST)

        if form.is_valid():
            desc = form.cleaned_data["token_desc"]

            try:
                duplicate_token = UserGeneratedToken.objects.filter(
                    user=request.user, description=desc
                ).first()

                if duplicate_token:
                    messages.error(
                        request, "Token with this description already exists."
                    )
                    return render(request, "profile_api_keys.html", context)

                token_obj = UserGeneratedToken.objects.create(
                    user=request.user,
                    description=desc,
                )
            except ValidationError as e:
                if (
                    e.messages
                    and e.messages[0] == "Users can create at most 10 API keys."
                ):
                    messages.error(request, e.messages[0])
                else:
                    messages.error(request, "An error occurred.")
                return render(request, "profile_api_keys.html", context)
            else:
                if not token_obj:
                    messages.error(request, "Token not created")
                    return render(request, "profile_api_keys.html", context)

                context.update({"token": token_obj.token})
                messages.success(
                    request,
                    "Token created successfully, please save it now:",
                )
                return render(request, "profile_api_keys.html", context=context)
        else:
            messages.error(request, "Invalid description")
            return render(request, "profile_api_keys.html", context=context)
    else:
        raise Http404


@login_required
def profile_personal_information(request):
    if not request.user.is_authenticated:
        return redirect('index')
    user = request.user

    # this is here because phone number was added later, and initial users did not
    # have it
    if not hasattr(request.user, "phone_number"):
        PhoneNumbers.objects.create(user=user)

    allowed_countries = [
                c.lower()
                for c in get_setting(
                    "phone_number_list_of_allowed_countries", default="us"
                ).strip().split(",")
            ]

    context = {
        "allowed_countries": allowed_countries,
        'phone_number': request.user.phone_number.number,
        'phone_number_is_validated': request.user.phone_number.is_validated,
    }
    if request.method == "GET":
        return render(request, "profile_personal_information.html", context)

    elif request.method == 'POST':
        action = request.POST.get('action')

        if action == 'verify':
            phone_number = request.POST.get('phone')
            allowed_country_codes = set([
                c.lower()
                for c in get_setting(
                    "phone_number_list_of_allowed_country_codes", default="+1"
                ).strip().split(",")
            ])
            if not phone_number or not any(
                    phone_number.startswith(code) for code in
                    allowed_country_codes):
                messages.error(
                    request,
                    "Invalid phone number. Only phone numbers with country "
                    f"codes starting with {allowed_country_codes} are allowed "
                    "at the moment."
                )
                return redirect('profile_personal_information')

            code = ''.join(random.choices(string.digits, k=6))

            # check if the number already exists
            if PhoneNumbers.objects.filter(
                    number=phone_number, is_validated=True
            ).exists():
                messages.error(
                    request,
                    "This phone number is already in use by another user."
                )
                return redirect('profile_personal_information')

            user.phone_number.number = phone_number
            user.phone_number.validation_code = code
            user.phone_number.save()

            try:
                send_user_sms_to_validate_phone_number(
                    to_phone_number=phone_number,
                    verification_code=code
                )

                messages.success(
                    request, "The verification code is being sent to your phone."
                )
            except Exception as e:
                logger.error(e)
                messages.error(
                    request,
                    "Failed to send code. If the problem persists, please "
                    "contact support."
                )

            return redirect('profile_personal_information')

        elif action == 'validate':
            verification_code = request.POST.get('verification_code')

            if verification_code != user.phone_number.validation_code:
                if (
                        user.phone_number.number_of_attempts
                        <= NUMBER_OF_PHONE_NUMBER_VERIFICATION_ATTEMPTS
                ):
                    user.phone_number.number_of_attempts += 1
                    user.phone_number.updated_at = get_current_date_time()
                    user.phone_number.save()
                    messages.error(
                        request,
                        "Invalid verification code. Please try again. Max "
                        "number of attempts: "
                        f"{NUMBER_OF_PHONE_NUMBER_VERIFICATION_ATTEMPTS}."
                    )
                else:
                    if (
                            user.phone_number.updated_at
                            > get_date_time_for_specified_hours_ago(hours=1)
                    ):
                        messages.error(
                            request,
                            "You have reached the maximum number of attempts. "
                            "Please try again in 1 hour."
                        )
                    else:  # reset the number of attempts, 1 hour has passed
                        user.phone_number.number_of_attempts = 0
                        user.phone_number.updated_at = get_current_date_time()
                        user.phone_number.save()

            elif verification_code == user.phone_number.validation_code:
                if PhoneNumbers.objects.filter(
                        number=user.phone_number.number, is_validated=True
                ).exists():
                    messages.error(
                        request,
                        "This phone number is already in use by another user. "
                        "Sorry, but we can't validate it for you. Please contact "
                        "support, or if you have 2 accounts, please delete one "
                        "phone number."
                    )
                    return redirect('profile_personal_information')

                user.phone_number.is_validated = True
                user.phone_number.save()

                set_redis_key(
                    REDIS_KEY_USER_PHONE_NUMBER.format(
                        number=user.phone_number.number
                    ),
                    simple_value=json.dumps(
                        {
                            "username": user.username,
                            "email": user.email,
                            "phone_number": user.phone_number.number
                        }
                    )
                )

                messages.success(request, "Phone number verified successfully.")

        elif action == 'delete':
            delete_redis_key(
                REDIS_KEY_USER_PHONE_NUMBER.format(
                    number=user.phone_number.number
                )
            )
            user.phone_number.number = None
            user.phone_number.is_validated = False
            user.phone_number.validation_code = None
            user.phone_number.number_of_attempts = 0
            user.phone_number.save()

            messages.success(request, "Your phone number has been deleted.")

        return redirect('profile_personal_information')

    else:
        raise Http404


@login_required
def profile_delete_api_keys(request, token_id):
    token = get_object_or_404(UserGeneratedToken, id=token_id)
    if token.user != request.user:
        messages.error(
            request, "You do not have permission to delete this token."
        )
        return redirect("profile_api_keys")

    if request.method == "GET":
        token.delete()
        messages.success(request, "Token deleted successfully.")
        return redirect("profile_api_keys")

    raise Http404


@login_required
def delete_my_user(request):
    """
    How it works:
    - we allow the user to delete their account if he does not have an active
    subscription. He will lose all credits.
    - if the user has an active metered subscription, he can't delete his account,
    he needs to cancel the subscription first.
    - if the user has a past_due subscription, he can't delete his account, he
    needs to pay the invoice first.
    - if the user has a monthly subscription, he can delete his account, but he
    will lose all credits.
    """

    generic_error_msg = (
        "There was an error when trying to delete your account. "
        "Please contact support for help.",
    )

    if not request.user.is_authenticated:
        messages.error(request, "You are not logged in.")
        return redirect("index")
    
    user_email = request.user.email

    if request.method.upper() != "POST":
        return redirect("profile_general")

    try:
        subs_item_obj = StripeSubscriptionItem.objects.get(
            user=request.user,
            is_deleted=False,
        )
    except StripeSubscriptionItem.DoesNotExist:
        try:
            delete_user_and_connected_data(user_obj=request.user)
        except CustomRequestException as e:
            logger.error(
                f"(1)Error when trying to delete user's connected data: {e}"
            )
            messages.error(request, generic_error_msg)
            raise Http404

        # No active subscription, delete user
        logout(request)
        messages.success(request, "Your account has been deleted.")
        send_user_delete_email_message.delay(to_email=user_email)

        return redirect("login")

    # this should never happen
    except StripeSubscriptionItem.MultipleObjectsReturned:
        logger.error(
            "Multiple StripeSubscriptionItem objects found for user "
            f"{request.user.username}."
        )
        messages.error(request, generic_error_msg)
        raise Http404

    if not subs_item_obj:
        # we should never get here
        logger.error(
            "There was an unknown error when trying to delete user "
            "account. No StripeSubscriptionItem object found for user: "
            f"{request.user.username}."
        )
        messages.error(request, generic_error_msg)
        raise Http404

    if subs_item_obj.is_active:
        msg = (
            "You can't delete your account while you have an active "
            f"<b>{subs_item_obj.pricing_plan.name}</b> subscription."
        )

        if subs_item_obj.cancel_at_period_end:
            msg += (
                "<br><br>Your subscription is set to cancel at the end of the "
                "current billing period on: <br>"
                f"<b>{subs_item_obj.end_date.strftime('%d-%m-%Y')}</b><br> After "
                "that period, you will be able to delete your account."
            )

        messages.error(request, mark_safe(msg))
        return redirect("profile_general")

    if (
        subs_item_obj.is_past_due
        or StripeInvoice.objects.filter(
            user=request.user, status="Payment failed"
        ).exists()
    ):
        messages.error(
            request,
            "You can't delete your account while you have an unpaid "
            "invoice. Please pay your invoice first.",
        )
        return redirect("profile_general")

    if not subs_item_obj.is_active:
        try:
            delete_user_and_connected_data(
                user_obj=request.user,
                subs_item_obj=subs_item_obj,
            )
        except CustomRequestException as e:
            logger.error(
                f"(2)Error when trying to delete user's connected data: {e}"
            )
            messages.error(request, generic_error_msg)
            raise Http404

        # No active subscription, delete user
        logout(request)
        messages.success(request, "Your account has been deleted.")
        send_user_delete_email_message.delay(to_email=user_email)
        return redirect("login")

    messages.error(
        request,
        "There was an unknown error when trying to delete your account. "
        "Please contact support for help.",
    )
    raise Http404


def google_login(request):
    google_auth_endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
    scope = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
    ]

    state = str(uuid.uuid4())

    request.session['oauth_state'] = state

    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'response_type': 'code',
        'scope': ' '.join(scope),
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state,
    }
    auth_url = f"{google_auth_endpoint}?{urlencode(params)}"
    return redirect(auth_url)


def google_callback(request):
    """
    Handles the callback from Google's OAuth 2.0 server.
    """
    standard_error_msg = (
        'Login failed. If this error persists, please contact support.'
    )
    code = request.GET.get('code')
    state = request.GET.get('state')

    # Verify state parameter for CSRF protection
    if not state or state != request.session.pop('oauth_state', None):
        logger.error('Invalid state parameter.')
        messages.error(request, standard_error_msg)
        return redirect('login')

    if not code:
        logger.error('No code provided for google callback.')
        messages.error(request, standard_error_msg)
        return redirect('login')

    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    try:
        token_response = requests.post(token_url, data=data)
        token_response.raise_for_status()
        tokens = token_response.json()
    except requests.RequestException as e:
        logger.error(f'Failed to obtain tokens: {e}')
        messages.error(request, standard_error_msg)
        return redirect('login')

    id_token = tokens.get('id_token')
    if not id_token:
        messages.error(request, 'No ID token provided.')
        return redirect('login')

    id_token = exchange_google_token_for_firebase_id_token(id_token)

    try:
        payload = fb_auth.verify_id_token(id_token)
    except fb_auth.InvalidIdTokenError as e:
        logger.error(f'Invalid ID token: {e}')
        messages.error(request, standard_error_msg)
        return redirect('login')
    except Exception as e:
        logger.error(f'Error verifying ID token: {e}')
        messages.error(request, standard_error_msg)
        return redirect('login')

    email = payload.get('email')
    if not email:
        logger.error('No email found in token.')
        messages.error(request, standard_error_msg)
        return redirect('login')

    if not payload.get('email_verified'):
        logger.error('Email not verified.')
        messages.error(request, standard_error_msg)
        return redirect('login')

    user = None
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        pass
    except CustomUser.MultipleObjectsReturned:
        logger.error(f'Multiple users found for email: {email}')
        messages.error(request, standard_error_msg)
    except Exception as e:
        logger.error(f'Error fetching user: {e}')
        messages.error(request, standard_error_msg)
        return redirect('login')

    if not user:
        try:
            firebase_user_id = payload.get('user_id')

            user = CustomUser.objects.create_user(
                username=firebase_user_id, email=email,
                normalized_email=get_normalized_email(email),
                stripe_customer_id=f"temp_customer_{generate_random_string()}",
                is_active=True,
            )

            stripe_customer = stripe.Customer.create(
                email=email,
                description=f"Customer for - {email}",
            )

            user.stripe_customer_id = stripe_customer.id
            user.set_unusable_password()
            user.save()

            # here we add the default Limit for Daily API calls
            set_redis_key(
                REDIS_KEY_USER_API_DAILY_CALL_LIMIT.format(
                    username=user.username
                ),
                simple_value=user.api_daily_call_limit,
            )

            msg = get_new_user_credit_message(user, is_sso=True)

            messages.success(request, msg)
        except Exception as e:
            logger.error(f'Error creating user: {e}')
            messages.error(request, standard_error_msg)
            return redirect('login')

    if not user:  # this second check is necessary
        logger.error('Failed to create user.')
        messages.error(request, standard_error_msg)
        return redirect('login')

    # Log the user in
    auth_login(request, user)

    # Redirect to the next page
    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url, allowed_hosts={request.get_host()}
    ):
        return redirect(next_url)
    return redirect('index')


def validate_email_view(request):
    token = request.GET.get('token')

    if not token:
        raise Http404

    try:
        user_pk = verify_email_token(token)
        if not user_pk:
            raise Http404

        user_obj = CustomUser.objects.get(pk=user_pk)
        fb_user = fb_auth.get_user_by_email(user_obj.email)
        if not user_obj or fb_user.email_verified:
            raise Http404

        # firebase activate user
        fb_user = fb_auth.get_user_by_email(user_obj.email)
        fb_auth.update_user(fb_user.uid, email_verified=True)

        # activate user
        user_obj.is_active = True
        user_obj.save()

        messages.success(
            request, 'Email verified successfully. You can now login.'
        )

        return redirect('login')

    except Exception as e:
        # log details about who made the request
        logger.error(
            f'Error verifying email verification token: {e}',
            extra={'request': request},
        )
        raise Http404


def password_reset(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method.upper() != "POST":
        token = request.GET.get('token')
    else:
        token = request.POST.get('token')

    try:
        user_pk = verify_email_token(token)
        if not user_pk:
            raise Http404

        if request.method == 'POST':
            form = SetNewPasswordForm(request.POST)
            if form.is_valid():

                password1 = form.cleaned_data['password1']
                password2 = form.cleaned_data['password2']

                validate_password(password1, password2)

                if password1 != password2:
                    form.add_error('password2', 'Passwords do not match.')
                else:
                    try:
                        user_obj = CustomUser.objects.get(pk=user_pk)
                        fb_user = fb_auth.get_user_by_email(user_obj.email)
                        fb_auth.update_user(fb_user.uid, password=password1)
                        messages.success(
                            request, 'Password has been reset successfully.'
                        )
                        user_obj.set_password(password1)
                        user_obj.save()

                        PasswordResetToken.objects.get(token=token).delete()

                        return redirect('login')
                    except:
                        messages.error(
                            request,
                            'An error occurred while resetting the password.'
                        )
        else:
            form = SetNewPasswordForm()

        return render(
            request, 'password_reset.html',
            {
                'form': form, 'token': token,
                "recaptcha_public_key": settings.RECAPTCHA_PUBLIC_KEY
            }
        )
    except CustomValidationError as e:
        messages.error(request, "Invalid password.")
        return redirect('login')

    except Exception as e:
        logger.error(f'Error verifying email verification token: {e}')
        messages.error(request, 'Password reset link is invalid or has expired.')
        return redirect('login')
