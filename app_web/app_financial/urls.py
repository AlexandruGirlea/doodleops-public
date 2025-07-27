from django.urls import path

from app_financial.views import (
    pricing_credits,
    create_credit_checkout_session,
    create_subscriptions_checkout_session,
    pricing_subscriptions,
    buy_credit_success_page,
    buy_subscription_success_page,
)

urlpatterns = [
    path("pricing-credits/", pricing_credits, name="pricing_credits"),
    path(
        "create-credit-checkout-session",
        create_credit_checkout_session,
        name="create_credit_checkout_session",
    ),
    path(
        "pricing-subscriptions/",
        pricing_subscriptions,
        name="pricing_subscriptions",
    ),
    path(
        "create-subscriptions-checkout-session",
        create_subscriptions_checkout_session,
        name="create_subscriptions_checkout_session",
    ),
    path(
        "buy-credit-success/",
        buy_credit_success_page,
        name="buy_credit_success_page",
    ),
    path(
        "buy-subscription-success/",
        buy_subscription_success_page,
        name="buy_subscription_success_page",
    ),
]
