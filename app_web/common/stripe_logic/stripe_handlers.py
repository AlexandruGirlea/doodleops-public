import logging

from app_users.models import CustomUser
from app_financial.models import (
    StripeSubscriptionItem,
    PricingBuySubscription,
    StripeInvoice,
    StripePaymentIntent,
)
from app_financial.utils import soft_delete_user_subscription_item
from common.stripe_logic.stripe_schemas import EVENT_OBJECT_TYPES
from common.stripe_logic.stripe_utils import (
    store_stripe_event_redis_sql,
    send_subscription_item_metered_usage_to_stripe,
)
from common.redis_logic.redis_utils import (
    add_one_time_credits_to_customer,
    set_credits_for_customer_subscription,
    set_user_subscription_false,
    set_user_subscription_active,
)
from common.date_time_utils import convert_timestamp_to_date


logger = logging.getLogger(__name__)


def handle_unknown_stripe_event(event: dict) -> None:
    customer_id = event.get("data", {}).get("object", {}).get("customer")
    try:
        user_obj = CustomUser.objects.get(stripe_customer_id=customer_id)
    except CustomUser.DoesNotExist:
        user_obj = None

    event_obj = store_stripe_event_redis_sql(
        event=event,
        user_obj=user_obj,
    )
    event_obj.error = "Unknown event type"
    event_obj.save()


def handle_stripe_customer(event: dict) -> None:
    """
    If a Stripe customer is created, we should have a user with that email.
    We don't need to handle customer.updated.
    """

    event_type = event.get("type")
    event_data_obj = event.get("data", {}).get("object", {})
    customer_id = event_data_obj.get("id")

    if (
        not customer_id
        or event_data_obj.get("object") != "customer"
        or event_type not in EVENT_OBJECT_TYPES.get("customer", [])
    ):
        logger.error("Not a customer object. Event: %s", event.get("id"))
        raise ValueError("Not a customer object")

    try:
        user_obj = CustomUser.objects.get(stripe_customer_id=customer_id)
    except CustomUser.DoesNotExist:
        user_obj = None

    store_stripe_event_redis_sql(
        event=event,
        user_obj=user_obj,
    )


def handle_stripe_subscription(event: dict) -> None:
    """
    We will not upsell subscriptions, so that we will not have to handle
    these types of events.
    """
    event_type = event.get("type")
    event_data_obj = event.get("data", {}).get("object", {})
    customer_id = event_data_obj.get("customer")
    subscription_id = event_data_obj.get("id")
    price_id = event.get("data", {}).get("object", {}).get("plan", {}).get("id")
    status = event.get("data", {}).get("object", {}).get("status")
    subscription_item_id = (
        event_data_obj.get("items", {}).get("data", [{}])[0].get("id")
    )
    # This is not always present.
    previous_attributes = event.get("data", {}).get("previous_attributes", {})

    error_msg = None
    if not customer_id:
        error_msg = f"Missing customer_id. Event id: {event.get('id')}"
    elif not subscription_id:
        error_msg = f"Missing subscription_id. Event id: {event.get('id')}"
    elif not price_id:
        error_msg = f"Missing price_id. Event id: {event.get('id')}"
    elif not status:
        error_msg = f"Missing status. Event id: {event.get('id')}"
    elif not subscription_item_id:
        error_msg = f"Missing subscription_item_id. Event id: {event.get('id')}"
    elif event_data_obj.get(
        "object"
    ) != "subscription" or event_type not in EVENT_OBJECT_TYPES.get(
        "subscription", []
    ):
        error_msg = f"Not a subscription object. Event id: {event.get('id')}"

    try:
        user_obj = CustomUser.objects.get(stripe_customer_id=customer_id)
    except CustomUser.DoesNotExist:
        user_obj = None
        error_msg = (
            f"Customer {customer_id} does not exist. Event id: {event.get('id')}"
        )

    if error_msg and user_obj:
        # Might be other events that we don't care about
        logger.warning(error_msg)
        store_stripe_event_redis_sql(event=event, user_obj=user_obj)
        return

    elif error_msg and not user_obj:
        logger.error(error_msg)
        raise ValueError(error_msg)

    # We store the event before we do anything else
    event_obj = store_stripe_event_redis_sql(
        event=event,
        user_obj=user_obj,
    )

    try:
        pricing_plan = PricingBuySubscription.objects.get(id=price_id)
    except PricingBuySubscription.DoesNotExist:
        msg = (
            f"PricingBuySubscription does not exist. Price id: {price_id}. "
            f"Event id: {event.get('id')}"
        )
        logger.error(msg)
        event_obj.error = msg
        event_obj.save()
        raise ValueError(msg)

    current_period_start = event_data_obj.get("current_period_start")
    current_period_end = event_data_obj.get("current_period_end")

    if not current_period_start or not current_period_end:
        msg = (
            "Missing current_period_start or current_period_end. "
            f"Event id: {event.get('id')}"
        )
        logger.error(msg)
        event_obj.error = msg
        event_obj.save()
        raise ValueError(msg)

    if event_type == "customer.subscription.created":
        """
        When creating a subscription Stripe behaves in 2 ways:
        - if it's a metered subscription, it creates a subscription item and it
        activates it immediately. Also it creates an invoice for 0$.
        - if it's a licensed subscription, it creates a subscription item with
        status incomplete and it activates it when the
        `customer.subscription.updated`


        We delete any old subscription item and create a new one, because
        of Stripe protection against multiple subscriptions per customer.
        """

        StripeSubscriptionItem.objects.filter(user=user_obj).delete()

        usage_type = (
            event_data_obj.get("items", {})
            .get("data", [{}])[0]
            .get("plan", {})
            .get("usage_type")
        )

        is_active = False
        if status == "incomplete" and usage_type == "licensed":
            is_active = False
        elif status == "active" and usage_type == "metered":
            is_active = True

        subs_item_obj = StripeSubscriptionItem.objects.create(
            id=subscription_item_id,
            subscription_id=subscription_id,
            user=user_obj,
            pricing_plan=pricing_plan,
            current_period_start=current_period_start,
            start_date=convert_timestamp_to_date(current_period_start),
            current_period_end=current_period_end,
            end_date=convert_timestamp_to_date(current_period_end),
            is_active=is_active,
            event_id=event_obj.id,
        )

        latest_invoice = event_data_obj.get("latest_invoice")
        if latest_invoice:
            try:
                invoice_obj = StripeInvoice.objects.get(
                    id=latest_invoice,
                    user=user_obj,
                )
                invoice_obj.subscription_item = subs_item_obj
                invoice_obj.save()
            except StripeInvoice.DoesNotExist:
                pass

        user_obj.api_daily_call_limit = pricing_plan.api_daily_call_limit
        user_obj.save()

        # because we don't get a `customer.subscription.updated` event
        if is_active:
            set_credits_for_customer_subscription(
                username=user_obj.username,
                api_daily_call_limit=pricing_plan.api_daily_call_limit,
            )

    elif event_type == "customer.subscription.updated":
        """
        For both subscription cancel and renew events, only register them
        as changes in the subscription item, but we don't change the user's
        api daily call limit or units. We should already have a
        StripeSubscriptionItem object created from the previous event.
        """
        try:
            subs_item_obj = StripeSubscriptionItem.objects.get(
                id=subscription_item_id
            )
        except StripeSubscriptionItem.DoesNotExist:
            msg = (
                "StripeSubscriptionItem does not exist. "
                f"Subscription item id: {subscription_item_id}. "
                f"Event id: {event.get('id')}"
            )
            logger.error(msg)
            raise StripeSubscriptionItem.DoesNotExist(msg)

        previous_current_period_start = previous_attributes.get(
            "current_period_start"
        )
        previous_current_period_end = previous_attributes.get(
            "current_period_end"
        )

        # Activating a newly created subscription.
        if (
            status == "active"
            and previous_attributes.get("status") == "incomplete"
            and current_period_start == subs_item_obj.current_period_start
            and current_period_end == subs_item_obj.current_period_end
            and not subs_item_obj.pricing_plan.is_metered
        ):
            subs_item_obj.is_active = True
            subs_item_obj.event_id = event_obj.id
            subs_item_obj.save()

            set_credits_for_customer_subscription(
                username=user_obj.username,
                api_daily_call_limit=pricing_plan.api_daily_call_limit,
                credits_monthly=pricing_plan.credits_monthly,
            )
            # redis
            set_user_subscription_active(
                username=user_obj.username,
            )

        # renewing a subscription, a month has passed.
        elif (
            subs_item_obj.is_active
            and status == "active"
            and previous_current_period_start
            == subs_item_obj.current_period_start
            and current_period_start > previous_current_period_start
            and previous_current_period_end == subs_item_obj.current_period_end
            and current_period_end > previous_current_period_end
        ):
            """
            previous_current_period_end might not be the same as
            current_period_start because of delays in the Stripe
            subscription renewals.
            """

            if not subs_item_obj.pricing_plan.is_metered:
                set_credits_for_customer_subscription(
                    username=user_obj.username,
                    api_daily_call_limit=pricing_plan.api_daily_call_limit,
                    credits_monthly=pricing_plan.credits_monthly,
                )
            else:
                send_subscription_item_metered_usage_to_stripe(
                    subs_item_obj=subs_item_obj,
                    is_stripe_webhook=True,
                )

            subs_item_obj.current_period_start = current_period_start
            subs_item_obj.start_date = convert_timestamp_to_date(
                current_period_start
            )

            subs_item_obj.current_period_end = current_period_end
            subs_item_obj.end_date = convert_timestamp_to_date(current_period_end)

            subs_item_obj.event_id = event.get("id")
            subs_item_obj.save()
            # redis
            set_user_subscription_active(
                username=user_obj.username,
            )

        # cancel
        elif (
            status == "active"
            and event_data_obj.get("cancel_at_period_end") is True
        ):
            subs_item_obj.cancel_at_period_end = True
            subs_item_obj.event_id = event.get("id")
            subs_item_obj.save()

        # reactivating a canceled subscription
        elif (
            status == "active"
            and previous_attributes.get("cancel_at")
            and event_data_obj.get("cancel_at_period_end") is False
            and previous_attributes.get("cancel_at_period_end") is True
        ):
            subs_item_obj.cancel_at_period_end = False
            subs_item_obj.event_id = event.get("id")
            subs_item_obj.save()

        elif status == "past_due":
            # we handle the subscription pause in the invoice action below
            subs_item_obj.is_past_due = True
            subs_item_obj.is_active = False
            subs_item_obj.save()
        elif (
            status == "active" and previous_attributes.get("status") == "past_due"
        ):
            # we handle the subscription re-activation in the invoice action below
            subs_item_obj.is_past_due = False
            subs_item_obj.is_active = True
            subs_item_obj.save()

    elif event_type == "customer.subscription.deleted":
        soft_delete_user_subscription_item(
            user_obj=user_obj,
            subscription_item_id=subscription_item_id,
        )


def handle_stripe_invoice(event: dict) -> None:
    """
    We only handle: created, paid.
    OBS a finalized invoice does not mean that it's paid.
    """
    event_type = event.get("type")
    event_data_obj = event.get("data", {}).get("object", {})
    invoice_id = event_data_obj.get("id")
    created = event_data_obj.get("created")
    customer_id = event_data_obj.get("customer")
    subscription_item_id = (
        event_data_obj.get("lines", {})
        .get("data", [{}])[0]
        .get("subscription_item")
    )
    price_id = (
        event_data_obj.get("lines", {})
        .get("data", [{}])[0]
        .get("price", {})
        .get("id")
    )
    amount_due = event_data_obj.get("amount_due")
    status = event_data_obj.get("status")

    if (
        not customer_id
        or event_data_obj.get("object") != "invoice"
        or event_type not in EVENT_OBJECT_TYPES.get("invoice", [])
    ):
        logger.error("Invalid invoice event: %s", event.get("id"))
        raise ValueError("Not a invoice object")

    try:
        user_obj = CustomUser.objects.get(stripe_customer_id=customer_id)
    except CustomUser.DoesNotExist:
        logger.error("Missing user_obj, event: %s", event)
        raise ValueError("Missing user_obj")

    try:
        price_obj = PricingBuySubscription.objects.get(id=price_id)
    except PricingBuySubscription.DoesNotExist:
        logger.error("Missing price_obj, event: %s", event)
        raise ValueError("Missing price_obj")

    try:
        subscription_item_obj = StripeSubscriptionItem.objects.get(
            id=subscription_item_id
        )
    except StripeSubscriptionItem.DoesNotExist:
        subscription_item_obj = None

    if event_type == "invoice.created" and status in {"open", "draft"}:
        if not StripeInvoice.objects.filter(id=invoice_id).exists():
            StripeInvoice.objects.create(
                id=invoice_id,
                event_id=event.get("id"),
                created=created,
                user=user_obj,
                price=price_obj,
                subscription_item=subscription_item_obj,
                amount_due=amount_due,
                status=status,
            )

    elif event_type == "invoice.paid" and status == "paid":
        try:
            invoice_obj = StripeInvoice.objects.get(id=invoice_id)
            invoice_obj.created = created
            invoice_obj.event_id = event.get("id")
            invoice_obj.status = status
            invoice_obj.save()
        except StripeInvoice.DoesNotExist:
            StripeInvoice.objects.create(
                id=invoice_id,
                event_id=event.get("id"),
                created=created,
                user=user_obj,
                price=price_obj,
                subscription_item=subscription_item_obj,
                amount_due=amount_due,
                status=status,
            )
    elif event_type == "invoice.payment_failed" and status == "open":
        try:
            invoice_obj = StripeInvoice.objects.get(id=invoice_id)
            invoice_obj.status = "payment_failed"
            invoice_obj.save()

            set_user_subscription_false(
                username=user_obj.username,
            )

        except StripeInvoice.DoesNotExist:
            logger.error("Missing invoice_obj, event: %s", event)

    elif event_type == "invoice.payment_succeeded" and status == "paid":
        try:
            invoice_obj = StripeInvoice.objects.get(id=invoice_id)
            invoice_obj.created = created
            invoice_obj.event_id = event.get("id")
            invoice_obj.status = status
            invoice_obj.save()

            set_user_subscription_active(
                username=user_obj.username,
            )

        except StripeInvoice.DoesNotExist:
            StripeInvoice.objects.create(
                id=invoice_id,
                event_id=event.get("id"),
                created=created,
                user=user_obj,
                price=price_obj,
                subscription_item=subscription_item_obj,
                amount_due=amount_due,
                status=status,
            )

    store_stripe_event_redis_sql(
        event=event,
        user_obj=user_obj,
    )


def handle_stripe_payment_intent(event: dict) -> None:
    """
    We use this for 2 things:
    1. When a user pays for a subscription, we only store the event.
    2. When a user pays for a one-time purchase, we update the user's credits.
    """

    event_type = event.get("type")
    event_data_obj = event.get("data", {}).get("object", {})

    created = event_data_obj.get("created")
    description = event_data_obj.get("description")
    invoice = event_data_obj.get("invoice")
    amount = event_data_obj.get("amount")
    status = event_data_obj.get("status")
    customer_id = event_data_obj.get("customer")

    if (
        not created
        or not customer_id
        or event_data_obj.get("object") != "payment_intent"
        or event_type not in EVENT_OBJECT_TYPES.get("payment_intent", [])
    ):
        logger.error("Invalid payment_intent event: %s", event.get("id"))
        raise ValueError("Not a payment_intent object")

    try:
        user_obj = CustomUser.objects.get(stripe_customer_id=customer_id)
    except CustomUser.DoesNotExist:
        logger.error("Missing user_obj, event: %s", event)
        raise ValueError("Missing user_obj")

    # this is a subscription payment
    if (
        description
        and "subscription" in description.lower()
        and status == "succeeded"
        and invoice
    ):
        try:
            invoice_obj = StripeInvoice.objects.get(id=invoice)
        except StripeInvoice.DoesNotExist:
            """
            This might be None based on the order in which Stripe sends the events
            """
            invoice_obj = None

        StripePaymentIntent.objects.create(
            id=event_data_obj.get("id"),
            event_id=event.get("id"),
            created=created,
            user=user_obj,
            invoice=invoice_obj,
            amount=amount,
            status="succeeded",
        )

    # this is a one time payment for credits
    elif not description and status == "succeeded" and not invoice:
        StripePaymentIntent.objects.create(
            id=event_data_obj.get("id"),
            event_id=event.get("id"),
            created=created,
            user=user_obj,
            amount=amount,
            status="succeeded",
        )

        add_one_time_credits_to_customer(
            user_obj=user_obj, amount_in_cents=amount
        )

    store_stripe_event_redis_sql(
        event=event,
        user_obj=user_obj,
    )
