from django.core.management.base import BaseCommand

from app_financial.tasks import (
    cronjob_send_subscription_item_metered_usage_to_stripe,
)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        cronjob_send_subscription_item_metered_usage_to_stripe.delay()
        print("We sent the metered usage to Stripe.")
