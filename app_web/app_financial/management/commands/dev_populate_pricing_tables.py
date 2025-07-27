import json
import time
import logging

import stripe
from django.core.management.base import BaseCommand
from django.conf import settings

from app_settings.utils import get_setting
from app_financial.models import (
    PricingBuyCredit,
    PricingBuySubscription,
    PricingBuySubscriptionTier,
)
from common.other import convert_cents_into_credit


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @staticmethod
    def process_price_one_time(price: stripe.Price) -> None:
        credits = convert_cents_into_credit(
            amount_in_cents=price.unit_amount, credit_type="one_time"
        )

        price_dict = {
            "id": price.id,
            "name": f"{credits} credits",
            "price_in_cents": price.unit_amount,
            "credits": credits,
        }

        PricingBuyCredit.objects.create(**price_dict)

    @staticmethod
    def process_price_subscription(
        price: stripe.Price,
    ) -> None:
        tiers = None
        if price.recurring.usage_type == "metered":
            if not price.metadata:
                raise ValueError(
                    "Metered subscription price must have metadata about tiers."
                )

            tiers = [json.loads(value) for key, value in price.metadata.items()]

        is_monthly = True if price.recurring.interval == "month" else False
        is_yearly = True if price.recurring.interval == "year" else False

        if price.unit_amount:
            if is_monthly:
                credits_monthly = convert_cents_into_credit(
                    amount_in_cents=price.unit_amount, credit_type="monthly"
                )
            elif is_yearly:
                credits_monthly = convert_cents_into_credit(
                    amount_in_cents=price.unit_amount, credit_type="yearly"
                )
            else:
                raise ValueError("Unknown interval")
        else:
            credits_monthly = None

        price_dict = {
            "id": price.id,
            "price_in_cents": price.unit_amount,
            "is_monthly": is_monthly,
            "is_yearly": is_yearly,
            "is_metered": (
                True
                if price.recurring.usage_type == "metered" and is_monthly
                else False
            ),
            "credits_monthly": credits_monthly,
        }

        product_id = price.product

        product = stripe.Product.retrieve(product_id)

        for k, v in product.metadata.items():
            price_dict[k] = int(v) if v.isnumeric() else v

        price_dict["name"] = product.name

        if price_dict["is_metered"]:
            price_dict["api_daily_call_limit"] = get_setting(
                "enterprise_api_daily_call_limit",
                default=10000,
            )
        elif price_dict.get("is_monthly"):
            price_dict["api_daily_call_limit"] = price_dict["price_in_cents"]
        elif price_dict.get("is_yearly"):
            # we divide by 10 because the yearly price is calculated as month * 10
            price_dict["api_daily_call_limit"] = price_dict["price_in_cents"] / 10

        price_obj = PricingBuySubscription.objects.create(**price_dict)

        if tiers:
            for tier in tiers:
                PricingBuySubscriptionTier.objects.create(
                    start=tier.get("start"),
                    end=tier.get("end"),
                    price_in_cents=tier.get("price_in_cents"),
                    flat_amount_in_cents=tier.get("flat_amount_in_cents"),
                    pricing_plan=price_obj,
                )

    def populate_prices(self):
        PricingBuyCredit.objects.all().delete()
        PricingBuySubscription.objects.all().delete()
        logger.info("Deleted all existing prices")

        # Fetch only active prices from Stripe
        price_objs = stripe.Price.list(active=True)
        logger.info("Fetched all active prices from Stripe")

        for price_obj in price_objs.data:
            if price_obj.type == "one_time":
                self.process_price_one_time(price_obj)
            elif price_obj.type == "recurring":
                self.process_price_subscription(price=price_obj)
            time.sleep(1)

    @staticmethod
    def set_display_order():
        prices = PricingBuyCredit.objects.all().order_by("price_in_cents")
        for i, price in enumerate(prices):
            price.display_order = i
            price.save()

        prices = PricingBuySubscription.objects.all().order_by("price_in_cents")

        last_display_number = 0
        for i, price in enumerate(prices):
            price.display_order = i
            price.save()
            last_display_number = i

        enterprise_price = PricingBuySubscription.objects.get(price_in_cents=None)
        enterprise_price.display_order = last_display_number + 1
        enterprise_price.save()

    def handle(self, *args, **kwargs):

        # one time only, run in prod
        if (
                settings.ENV_MODE == "prod" and not
                PricingBuySubscription.objects.first() and not
                PricingBuyCredit.objects.first() and not
                PricingBuySubscriptionTier.objects.first()
        ):
            self.populate_prices()
            self.set_display_order()
            print("Prod Prices have been created")

        elif settings.ENV_MODE in {"local", "dev"}:
            self.populate_prices()
            self.set_display_order()
            print("Dummy prices have been created")
        else:
            self.stdout.write(
                self.style.ERROR(
                    "This command is only for Local and Dev environments."
                )
            )
