import time
import logging
from dateutil.relativedelta import relativedelta

from celery import shared_task

from app_financial.models import (
    CustomerCreditsBought, StripeSubscriptionItem, PricingBuySubscription
)
from app_financial.utils import (
    charge_deleted_metered_subscription_draft_invoices,
)
from common.stripe_logic.stripe_schemas import (
    EVENT_OBJECT_TYPES,
    IGNORED_EVENT_TYPES,
)
from common.stripe_logic.stripe_handlers import (
    handle_unknown_stripe_event,
    handle_stripe_customer,
    handle_stripe_subscription,
    handle_stripe_payment_intent,
    handle_stripe_invoice,
)
from common.stripe_logic.stripe_utils import (
    send_subscription_item_metered_usage_to_stripe,
)
from common.redis_logic.custom_redis import delete_redis_key
from common.redis_logic.redis_utils import set_credits_for_customer_subscription
from common.redis_logic.redis_schemas import REDIS_KEY_USER_CREDIT_BOUGHT
from common.date_time_utils import get_current_date_time

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(StripeSubscriptionItem.DoesNotExist,),
    retry_kwargs={'max_retries': 10, 'countdown': 20},
    retry_backoff=False
)
def stripe_handle_any_event(event: dict) -> None:
    event_type = event.get("type")
    event_object_type = event.get("data", {}).get("object", {}).get("object")

    if event_type in IGNORED_EVENT_TYPES:
        return
    if event_type not in EVENT_OBJECT_TYPES.get(event_object_type, []):
        logger.error("Unhandled event type: %s", event_type)
        return

    try:
        if event_object_type == "customer":
            handle_stripe_customer(event=event)

        # only subscriptions
        elif event_object_type == "subscription":
            handle_stripe_subscription(event=event)

        # only subscriptions
        elif event_object_type == "invoice":
            handle_stripe_invoice(event=event)

        # both subscription and credit
        elif event_object_type == "payment_intent":
            handle_stripe_payment_intent(event=event)

        # store log of stripe event in redis and sql
        else:
            handle_unknown_stripe_event(event=event)

    except StripeSubscriptionItem.DoesNotExist as e:
        raise e

    except Exception as e:
        logger.error("Error while handling event: %s, Error: %s", event, str(e))


@shared_task
def remove_expired_credits():
    """
    This task will be run every day at midnight + 2 minutes.
    It will remove expired credits.
    """
    for cred_bought_obj in CustomerCreditsBought.objects.filter(
        expires__lte=get_current_date_time()
    ):
        delete_redis_key(
            key=REDIS_KEY_USER_CREDIT_BOUGHT.format(
                username=cred_bought_obj.user.username,
                id=cred_bought_obj.id,
            )
        )

        cred_bought_obj.delete()


@shared_task
def cronjob_send_subscription_item_metered_usage_to_stripe():
    """
    This task will be run every 3 hours.
    It will send the metered usage to Stripe.
    """
    all_metered_subs_item_objs = StripeSubscriptionItem.objects.filter(
        pricing_plan__is_metered=True,
        is_active=True,
        is_deleted=False,
    )

    for sub_item_obj in all_metered_subs_item_objs:
        time.sleep(0.5)  # to avoid rate limit
        send_subscription_item_metered_usage_to_stripe(subs_item_obj=sub_item_obj)


@shared_task
def task_charge_deleted_metered_subscription_draft_invoices() -> None:
    """
    This task will be run every hour or when initiated by webhooks.
    This is possible because we do a soft deleting of the subscription item.
    """
    return charge_deleted_metered_subscription_draft_invoices()


@shared_task
def task_add_monthly_credits_to_yearly_subscriptions() -> None:
    yearly_pricing_plans = PricingBuySubscription.objects.filter(
        is_yearly=True
    )
    current_date_time = get_current_date_time()
    one_month_ago = current_date_time - relativedelta(months=1)

    to_update = []

    for pricing_plan in yearly_pricing_plans:
        for yearly_subscription_item in StripeSubscriptionItem.objects.filter(
                pricing_plan=pricing_plan,
                is_active=True,
                is_past_due=False,
                is_deleted=False,
                last_updated__lt=one_month_ago
        ):
            set_credits_for_customer_subscription(
                username=yearly_subscription_item.user.username,
                api_daily_call_limit=pricing_plan.api_daily_call_limit,
                credits_monthly=pricing_plan.credits_monthly,
            )

            yearly_subscription_item.last_updated = current_date_time

            to_update.append(yearly_subscription_item)

    StripeSubscriptionItem.objects.bulk_update(to_update, ["last_updated"])
