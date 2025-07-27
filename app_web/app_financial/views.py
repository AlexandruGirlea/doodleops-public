"""Use this link to test transactions: https://stripe.com/docs/testing"""
import json
import logging

import stripe
from django.urls import reverse
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, Http404

from app_financial.tasks import stripe_handle_any_event
from app_financial.models import (
    PricingBuyCredit,
    PricingBuySubscription,
    StripeSubscriptionItem,
    EnterpriseUser
)
from app_settings.utils import get_setting
from common.stripe_logic.stripe_utils import (
    webhook_construct_event,
    check_if_customer_has_already_a_subscription_item,
    delete_any_draft_subscription_that_the_customer_might_have,
)
from common.other import DEFAULT_API_DAILY_CALL_LIMIT

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    if request.method.upper() != "POST":
        return HttpResponseBadRequest("Invalid request")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        return HttpResponseBadRequest("Invalid request")

    event = webhook_construct_event(
        payload=payload,
        sig_header=sig_header,
        secret=endpoint_secret,
    )

    if not event and not settings.DEBUG:
        logger.error("Could not construct event for payload: {}".format(payload))
        return HttpResponseBadRequest("Invalid request")
    elif not event and settings.DEBUG:
        """
        We had to do this for testing purposes, because Stripe doesn't allow
        us to build event object when we change the local machine Time.
        """
        event = json.loads(payload)

    stripe_handle_any_event.apply_async(args=[event])
    return HttpResponse(status=200)


def pricing_credits(request):
    if request.method.upper() != "GET":
        raise Http404

    buy_credits = PricingBuyCredit.objects.all().order_by("price_in_cents")
    for credit in buy_credits:
        credit.price_in_dollars = int(credit.price_in_cents / 100)

    context = {
        "stripe_key": settings.STRIPE_PUBLISHABLE_KEY,
        "buy_credits": buy_credits,
        "default_api_daily_call_limit": DEFAULT_API_DAILY_CALL_LIMIT,
        "credits_expire_days": get_setting(key="credits_expire_days", default=90)
    }

    if request.user.is_authenticated:
        try:
            subs_item = StripeSubscriptionItem.objects.get(
                user=request.user, is_active=True
            )
            if subs_item.pricing_plan.is_metered:
                context["metered_subscription_name"] = subs_item.pricing_plan.name
        except StripeSubscriptionItem.DoesNotExist:
            pass

    return render(request, "pricing_credits.html", context)


def create_credit_checkout_session(request):
    if request.method.upper() != "GET":
        raise Http404

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"})

    try:
        subs_item = StripeSubscriptionItem.objects.get(
            user=request.user, is_active=True
        )
        if subs_item.pricing_plan.is_metered:
            return JsonResponse(
                {
                    "error": "You can't buy credit if you have a "
                    f"{subs_item.pricing_plan.name} subscription."
                }
            )
    except StripeSubscriptionItem.DoesNotExist:
        pass

    try:
        product_dollar_price = request.GET.get("price")
        customer_id = request.user.stripe_customer_id

        if f"{product_dollar_price}00" not in {  # in cents
            str(credit.price_in_cents)
            for credit in PricingBuyCredit.objects.all()
        }:
            return JsonResponse({"error": "Invalid amount"})

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"${product_dollar_price} Product",
                        },
                        "unit_amount": int(product_dollar_price) * 100,
                        "tax_behavior": "exclusive",
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=request.build_absolute_uri(
                reverse("buy_credit_success_page")
            ),
            cancel_url=request.build_absolute_uri(reverse("pricing_credits")),
            customer=customer_id,
            billing_address_collection='required',
            tax_id_collection={"enabled": True},
            automatic_tax={"enabled": True},
            customer_update={"name": "auto", "address": "auto"},
            invoice_creation={
                "enabled": True,
                "invoice_data": {
                    "description": (
                        "Invoice for one-time purchase from "
                        "DoodleOps (S.C. Acme Corporation S.R.L.)"
                    ),

                    "custom_fields": [
                        {
                            "name": "VAT ID",
                            "value": "RO123456789"
                        },
                        {
                            "name": "Company Reg. No.",
                            "value": "J11111/2025"
                        }
                    ],

                    "footer": (
                        "S.C. Acme Corporation S.R.L. | "
                        "Romania (European Union)"
                    ),

                    "metadata": {
                        "notes": "Thank you for your purchase!"
                    },

                    "rendering_options": {
                        "amount_tax_display": "exclude_tax"
                    }
                }
            },
        )
        return JsonResponse({"session_id": session.id})

    except Exception as e:
        logger.exception("Error creating checkout session: %s", e)
        return JsonResponse({"error": "Unknown error"})


def pricing_subscriptions(request):
    if request.method != "GET":
        raise Http404

    context = {
        "can_buy_enterprise": False, "has_subscription": False,
        "calendly_url": get_setting('calendly_url'),
    }

    if request.user.is_authenticated:
        if check_if_customer_has_already_a_subscription_item(
            user_obj=request.user
        ):
            context["has_subscription"] = True

        if EnterpriseUser.objects.filter(user=request.user).exists():
            context["can_buy_enterprise"] = True

    enterprise_tiers = []

    buy_subscriptions = PricingBuySubscription.objects.all().order_by(
        "display_order"
    )

    for subs in buy_subscriptions:
        subs.api_daily_call_limit = "{:,}".format(
            subs.api_daily_call_limit
        ).replace(",", " ")

        if subs.price_in_cents:
            subs.price_in_dollars = int(subs.price_in_cents / 100)

        elif subs.is_metered:
            enterprise_tiers = subs.pricing_plan_tiers.all().order_by("start")

            for t in enterprise_tiers:
                if t.start:
                    t.start = "{:,}".format(t.start).replace(",", " ")
                if t.end:
                    t.end = "{:,}".format(t.end).replace(",", " ")

                t.price_in_dollars = t.price_in_cents / 100
                t.flat_amount_in_dollars = int(t.flat_amount_in_cents / 100)

            if enterprise_tiers:
                subs.flat_amount_in_dollars = int(
                    enterprise_tiers[0].flat_amount_in_cents / 100
                )

    context["stripe_key"] = settings.STRIPE_PUBLISHABLE_KEY
    context["buy_subscriptions"] = buy_subscriptions
    context["enterprise_tiers"] = enterprise_tiers

    return render(request, "pricing_subscriptions.html", context)


def create_subscriptions_checkout_session(request):
    if request.method != "GET":
        raise Http404

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"})

    try:
        pricing_plan_id = request.GET.get("pricing_plan_id")

        customer_id = request.user.stripe_customer_id

        if not delete_any_draft_subscription_that_the_customer_might_have(
            customer_id=customer_id
        ):
            return JsonResponse(
                {
                    "error": "Looks like you have a draft subscription, that "
                             "could not be deleted. Please try again later. If "
                             "the problem persists, please contact support."
                }
            )

        pricing_buy_subs_obj = PricingBuySubscription.objects.filter(
            id=pricing_plan_id
        ).first()

        if (
                pricing_buy_subs_obj.is_metered and
                not EnterpriseUser.objects.filter(user=request.user).exists()
        ):
            raise Http404

        if not pricing_buy_subs_obj:
            return JsonResponse({"error": "Invalid subscription"})

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=(
                [{"price": pricing_plan_id}]
                if pricing_buy_subs_obj.is_metered
                else [{"price": pricing_plan_id, "quantity": 1}]
            ),
            mode="subscription",
            success_url=request.build_absolute_uri(
                reverse("buy_subscription_success_page")
            ),
            cancel_url=request.build_absolute_uri(
                reverse("pricing_subscriptions")
            ),
            customer=customer_id,
            billing_address_collection='required',
            tax_id_collection={"enabled": True},
            automatic_tax={"enabled": True},
            customer_update={"name": "auto", "address": "auto"},
        )
        return JsonResponse({"session_id": session.id})

    except Exception as e:
        logger.exception("Error creating checkout session: %s", e)
        return JsonResponse({"error": "Unknown error"})


def buy_credit_success_page(request):
    return render(request, "buy_credit_success_page.html")


def buy_subscription_success_page(request):
    return render(request, "buy_subscription_success_page.html")
