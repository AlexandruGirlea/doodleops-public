from django.core.management.base import BaseCommand

from app_financial.tasks import remove_expired_credits


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        remove_expired_credits.delay()
        print("We Removed expired credits.")
