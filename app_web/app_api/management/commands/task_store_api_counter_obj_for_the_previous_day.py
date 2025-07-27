from django.core.management.base import BaseCommand

from app_api.tasks import cronjob_store_api_counter_obj_for_the_previous_day


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        cronjob_store_api_counter_obj_for_the_previous_day.delay()
        print("We stored the API counters for the previous day.")
