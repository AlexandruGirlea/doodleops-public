import random
from datetime import timedelta, date

import django
from django.core.management.base import BaseCommand
from django.conf import settings

from app_users.models import CustomUser
from app_api.models import APICounter

APIs = [
    v + str(random.randint(1, 100))
    for v in [
        "v1_image_to_black_and_white",
        "v1_image_to_color",
        "v1_pdf_to_image",
        "v2_pdf_to_image",
    ]
]


class Command(BaseCommand):
    @staticmethod
    def create_api_counter_objects(username, count=100):
        base_date = date.today()

        for i in range(count):
            try:
                api_name = APIs[random.randint(0, len(APIs) - 1)]
                credits_used = random.randint(1, 100)
                days_difference = timedelta(days=random.randint(1, 365))
                random_date = base_date - days_difference

                # Create the new APICounter object
                APICounter.objects.create(
                    username=username,
                    api_name=api_name,
                    number_of_calls=random.randint(1, 100),
                    date=random_date,
                    credits_used=credits_used,
                )
            except django.db.utils.IntegrityError:
                continue

    def handle(self, *args, **kwargs):
        if settings.ENV_MODE not in {"local", "dev"}:
            self.stdout.write(
                self.style.ERROR(
                    "This command is only for Local and Dev environments."
                )
            )
            return

        user_obj = CustomUser.objects.filter(
            email="alex@doodleops.com"
        ).first()

        if user_obj:
            self.create_api_counter_objects(user_obj.username)
            print(APICounter.objects.all().count())
