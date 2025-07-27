import stripe
from firebase_admin import auth as fb_auth
from django.core.management.base import BaseCommand
from django.conf import settings

from app_users.models import CustomUser
from app_users.utils import create_user


DUMMY_USER_TEMPLATE = {
    "email": "alex@doodleops.com",
    "password": "Admin123@",
}

match settings.ENV_MODE:
    case "local":
        NUMBER_OF_TEST_USERS = 2
    case "dev":
        NUMBER_OF_TEST_USERS = 1
    case _:
        NUMBER_OF_TEST_USERS = 0


class Command(BaseCommand):
    @staticmethod
    def delete_all_firebase_users():
        def delete_firebase_users_in_batch(users):
            for user in users:
                try:
                    fb_auth.delete_user(user.uid)
                    print(f"Successfully deleted user: {user.uid}")
                except Exception as e:
                    print(f"Error deleting user: {user.uid}, {e}")

        page = fb_auth.list_users()

        while page:
            delete_firebase_users_in_batch(page.users)
            # Get next batch of users
            page = page.get_next_page()

    @staticmethod
    def delete_all_stripe_customers():
        customers = stripe.Customer.list()  # Get all customers

        for customer in customers:
            print(f"Deleting customer with ID: {customer.id}")
            stripe.Customer.delete(customer.id)

    def create_dummy_users(self):
        self.delete_all_firebase_users()
        self.delete_all_stripe_customers()

        CustomUser.objects.all().delete()

        for n in range(NUMBER_OF_TEST_USERS):
            if n == 0:
                email = DUMMY_USER_TEMPLATE["email"]
            else:
                email_split = DUMMY_USER_TEMPLATE["email"].split("@")
                email = email_split[0] + "+" + str(n) + "@" + email_split[1]

            user_obj, _ = create_user(
                email=email,
                password1=DUMMY_USER_TEMPLATE["password"],
                password2=DUMMY_USER_TEMPLATE["password"],
                email_verified=True,
            )

            user_obj.__dict__.update(
                {
                    "first_name": f"first_name{n}",
                    "last_name": f"last_name{n}",
                    "is_superuser": True if n == 0 else False,
                    "is_staff": True if n == 0 else False,
                }
            )
            user_obj.save()

    def handle(self, *args, **kwargs):
        # DO NOT REMOVE THIS CHECK. We should not run this in PROD.
        if settings.ENV_MODE not in {"local", "dev"}:
            self.stdout.write(
                self.style.ERROR(
                    "This command is only for Local and Dev environments."
                )
            )
            return
        self.create_dummy_users()
        print("Dummy users have been created")
        print("Use the following credentials to login:")
        print(DUMMY_USER_TEMPLATE["email"])
        print(DUMMY_USER_TEMPLATE["password"])
