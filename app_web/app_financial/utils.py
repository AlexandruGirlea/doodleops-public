import time
import logging

import stripe

from app_users.models import CustomUser, UserGeneratedToken
from app_financial.models import StripeSubscriptionItem
from common.redis_logic.custom_redis import set_redis_key, delete_redis_key
from common.redis_logic.redis_schemas import (
    REDIS_KEY_USER_API_DAILY_CALL_LIMIT,
    REDIS_KEY_METERED_SUBSCRIPTION_USERS,
    REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
    REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION,
)
from common.redis_logic.redis_utils import (
    calculate_metered_cost_based_on_tier,
)
from common.other import DEFAULT_API_DAILY_CALL_LIMIT

logger = logging.getLogger(__name__)


def charge_deleted_metered_subscription_draft_invoices(
    username: str = None,
) -> None:
    """
    This function is run both as cronjob and on demand.

    Step 1. See if there are any draft invoices for the user.
    Step 2. See if the draft invoice matches the calculated usage.
    Step 3'. If the draft invoice matches the calculated usage, pay the invoice.

    Step3''. if the draft invoice does not match the calculated usage, calculate
             the difference and create an additional invoice item for the
             difference.
    Step 4. Charge the user for the invoice.
    """
    if username:
        list_of_subs_item_objs = StripeSubscriptionItem.objects.filter(
            pricing_plan__is_metered=True,
            is_deleted=True,
            user__username=username,
        )
    else:
        list_of_subs_item_objs = StripeSubscriptionItem.objects.filter(
            pricing_plan__is_metered=True, is_deleted=True
        )

    for subs_item_obj in list_of_subs_item_objs:
        invoice_list = stripe.Invoice.list(
            customer=subs_item_obj.user.stripe_customer_id, status="draft"
        )

        if not invoice_list:
            continue

        for invoice_obj in invoice_list:
            total_excluding_tax_in_cents = invoice_obj.total_excluding_tax
            cost, credits_used = calculate_metered_cost_based_on_tier(
                subs_item_obj=subs_item_obj,
            )

            if total_excluding_tax_in_cents < cost:
                difference_in_cents = cost - total_excluding_tax_in_cents
                stripe.InvoiceItem.create(
                    customer=subs_item_obj.user.stripe_customer_id,
                    amount=difference_in_cents,
                    currency="usd",
                    description=f"Additional usage for "
                    f"{subs_item_obj.pricing_plan.name}. Total "
                    f"credis used: {credits_used}.",
                    invoice=invoice_obj.id,
                )
                stripe.Invoice.pay(invoice_obj.id)

            else:
                stripe.Invoice.pay(invoice_obj.id)


def soft_delete_user_subscription_item(
    user_obj: CustomUser, subscription_item_id: str
) -> None:
    try:
        subs_item_obj = StripeSubscriptionItem.objects.get(
            id=subscription_item_id
        )

        subs_item_obj.is_active = False
        subs_item_obj.is_deleted = True
        subs_item_obj.save()

    except (
        StripeSubscriptionItem.DoesNotExist
        or StripeSubscriptionItem.MultipleObjectsReturned
    ):
        logger.error(
            f"Could not find subscription item with id: {subscription_item_id}"
        )
        return

    if subs_item_obj.pricing_plan.is_metered:
        UserGeneratedToken.objects.filter(user=user_obj).delete()

    set_redis_key(
        REDIS_KEY_USER_API_DAILY_CALL_LIMIT.format(username=user_obj.username),
        simple_value=DEFAULT_API_DAILY_CALL_LIMIT,
    )

    delete_redis_key(
        key=REDIS_KEY_METERED_SUBSCRIPTION_USERS.format(
            username=user_obj.username
        )
    )

    delete_redis_key(
        key=REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
            username=user_obj.username
        )
    )

    delete_redis_key(
        key=REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION.format(
            username=user_obj.username
        )
    )

    # revert the user's api daily call limit to the default
    user_obj.api_daily_call_limit = DEFAULT_API_DAILY_CALL_LIMIT
    user_obj.save()

    if subs_item_obj.pricing_plan.is_metered:
        time.sleep(5)  # wait for Stripe to process the usage record

        # charge the user for the last month's usage
        charge_deleted_metered_subscription_draft_invoices(
            username=user_obj.username
        )
