import logging
import functools
import time
from typing import Any, Callable, Union, Optional

import stripe

from app_users.models import CustomUser
from app_financial.models import (
    StripeEvent,
    StripeSubscriptionItem,
)
from app_api.tasks import cronjob_store_api_counter_obj_for_the_previous_day
from common.redis_logic.custom_redis import set_redis_key
from common.redis_logic.redis_schemas import (
    REDIS_KEY_STRIPE_CUSTOMER_ID_EVENTS,
)
from common.redis_logic.redis_utils import (
    get_credits_used_per_metered_subscription_item,
)
from common.date_time_utils import get_current_timestamp

logger = logging.getLogger(__name__)


def handle_stripe_errors(return_value: Optional[Any] = None) -> Callable:
    """
    Decorator to handle Stripe errors in a unified manner.
    :param return_value: Default return value if an error is caught.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except stripe.error.InvalidRequestError as e:
                logger.error(f"Invalid request error: {e}")
            except stripe.error.RateLimitError as e:
                logger.error(f"Rate limit error: {e}")
            except stripe.error.AuthenticationError as e:
                logger.error(f"Authentication error: {e}")
            except stripe.error.APIConnectionError as e:
                logger.error(f"API connection error: {e}")
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
            return return_value

        return wrapper

    return decorator


def store_stripe_event_in_redis(
    customer_id: str, event_type: str, event_id: str, event: dict
) -> None:
    """Store the Stripe event in Redis, for 60 days."""
    set_redis_key(
        key=REDIS_KEY_STRIPE_CUSTOMER_ID_EVENTS.format(
            customer_id=customer_id,
            event_type=event_type,
            event_id=event_id,
        ),
        timed_value=event,
        expire=60 * 60 * 24 * 60,  # 60 days
        timestamp=event.get("created"),
    )


def store_stripe_event_in_sql(
    user_obj: CustomUser,
    event_type: str,
    event_id: str,
    event: dict,
) -> StripeEvent:
    try:
        event_obj = StripeEvent.objects.get(id=event_id)
    except StripeEvent.DoesNotExist:
        event_obj = StripeEvent.objects.create(
            id=event_id,
            user=user_obj if user_obj else None,
            event_type=event_type,
            event_object=event,
        )
    except Exception as e:
        logger.error(f"Error while storing Stripe event in SQL: {e}")
        raise e

    return event_obj


def store_stripe_event_redis_sql(
    event: dict,
    user_obj: CustomUser = None,
) -> StripeEvent:
    event_type = event.get("type")
    event_id = event.get("id")

    if not user_obj:
        customer_id = f"unknown_customer_id_{event_id}"
    else:
        customer_id = user_obj.stripe_customer_id

    store_stripe_event_in_redis(
        customer_id=customer_id,
        event_type=event_type,
        event_id=event_id,
        event=event,
    )

    return store_stripe_event_in_sql(
        user_obj=user_obj,
        event_type=event_type,
        event_id=event_id,
        event=event,
    )


@handle_stripe_errors(return_value=None)
def get_latest_metered_subscription_item_usage(
    subscription_item_id: str,
) -> Union[int, None]:
    """
    This is not used, but is useful to query the Stripe API directly based on
    a specific subscription_item_id.
    This function will return the total usage of a metered Subscription Item
    for the current billing period.
    """
    usage_records = stripe.SubscriptionItem.list_usage_record_summaries(
        subscription_item_id, limit=1
    )
    if usage_records and usage_records.data:
        return usage_records.data[0].total_usage


@handle_stripe_errors(return_value=None)
def get_stripe_customer_portal_url(
    customer_id: str,
    return_url: Union[str, None] = None,
) -> Union[str, None]:
    """
    This function will return the Stripe Customer Portal URL for the given
    customer_id and return_url.
    """
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


@handle_stripe_errors(return_value=None)
def create_metered_usage_for_subscription_item_by_setting_a_value(
    subscription_item_id: str, quantity: int, timestamp: int = None
):
    stripe.SubscriptionItem.create_usage_record(
        subscription_item_id,
        quantity=quantity,
        timestamp=timestamp if timestamp else get_current_timestamp(),
        action="set",
    )


@handle_stripe_errors(return_value=None)
def webhook_construct_event(
    payload: str,
    sig_header: str,
    secret: str,
) -> Union[stripe.Event, None]:
    """
    This function will construct a Stripe Event object from the given payload
    and sig_header.
    """
    try:
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=secret,
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error("x"*50)
        logger.error(f"payload: {payload}")
        logger.error("x" * 50)
        logger.error(f"sig_header: {sig_header}")
        logger.error("x" * 50)
        logger.error(f"secret: {secret}")
        logger.error("x" * 50)
        logger.error(f"Invalid Stripe signature: {e}")
        return None


@handle_stripe_errors(return_value=None)
def send_subscription_item_metered_usage_to_stripe(
    subs_item_obj: StripeSubscriptionItem,
    is_stripe_webhook: bool = False,
) -> None:
    """
    This method will be run on demand to send the metered usage of a
    subscription item to Stripe.

    This relies only on data available in APICounter model.

    If is_stripe_webhook is True, it will also calculate the previous day's
    usage and send it to Stripe.
    """
    if not subs_item_obj:
        logger.error("Missing subscription item.")
        return
    if not subs_item_obj.is_active or not subs_item_obj.pricing_plan.is_metered:
        logger.error(
            "Trying to send metered info for invalid subscription item, "
            f"requested for subs item id: {subs_item_obj.id}."
        )
        return

    username = subs_item_obj.user.username

    # make the calculation for the previous day instantly
    if is_stripe_webhook:
        result = cronjob_store_api_counter_obj_for_the_previous_day.apply_async(
            kwargs={"username": username}
        )

        if not result.get():
            logger.error(
                "Could not calculate the previous day's API usage for "
                f"username: {username}"
            )
            return

    quantity = get_credits_used_per_metered_subscription_item(
        subs_item_obj=subs_item_obj,
    )

    timestamp_to_set = get_current_timestamp()
    if is_stripe_webhook and subs_item_obj.current_period_end < timestamp_to_set:
        """
        The logic here is that if the current_period_end is less than the
        current timestamp,  we set the timestamp to the current_period_end - 1,
        so that the usage record will be accepted by Stripe.
        """
        timestamp_to_set = int(subs_item_obj.current_period_end - 1)

    create_metered_usage_for_subscription_item_by_setting_a_value(
        subscription_item_id=subs_item_obj.id,
        quantity=quantity,
        timestamp=timestamp_to_set,
    )


@handle_stripe_errors()
def delete_any_draft_subscription_that_the_customer_might_have(
    customer_id: str,
) -> bool:
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id, status="all"
        )
    except stripe.error.InvalidRequestError:
        return True

    for sub in subscriptions:
        if sub.status not in {"draft", "incomplete"}:
            continue

        stripe.Subscription.delete(sub.id)
        logger.info(f"Deleted draft subscription with id: {sub.id}.")
        time.sleep(2)  # wait 2 seconds to give Stripe time to process the delete

        deleted_subs = stripe.Subscription.retrieve(sub.id)
        if deleted_subs.status not in {"canceled", "incomplete_expired"}:
            logger.error(
                f"Could not delete draft subscription with id: {sub.id}."
            )
            return False

    return True


@handle_stripe_errors()
def check_if_customer_has_already_a_subscription_item(
    user_obj: CustomUser,
) -> bool:
    """
    This function will check if the given customer id has already a subscription
    item and return it if it exists.
    """
    try:
        if StripeSubscriptionItem.objects.get(
            user=user_obj,
            is_active=True,
        ):
            return True

    except (
        StripeSubscriptionItem.DoesNotExist
        or StripeSubscriptionItem.MultipleObjectsReturned
    ):
        pass

    if stripe.Subscription.list(
        customer=user_obj.stripe_customer_id, status="active"
    ):
        return True

    return False
