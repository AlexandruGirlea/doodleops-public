from django.core.management.base import BaseCommand

from app_api.tasks import has_api_counter_discrepancies


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        has_api_counter_discrepancies.delay()
        print("See Celery Worker output for discrepancies.")
