from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
from django.conf import settings

from common.redis_logic.custom_redis import delete_all_keys

class Command(BaseCommand):
    help = 'Forcefully removes all data from the database tables on LOCAL and DEV environments using DROP.'

    def handle(self, *args, **options):
        if settings.ENV_MODE not in {"local", "dev"}:
            self.stdout.write(
                self.style.ERROR(
                    "This command is only for Local and Dev environments."
                )
            )
            return

        self.stdout.write(self.style.WARNING('Starting to drop all tables...'))

        try:
            with connections['default'].cursor() as cursor:
                try:
                    # Disable foreign key checks
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                    self.stdout.write(self.style.NOTICE('Foreign key checks disabled.'))

                    # Fetch all table names
                    cursor.execute("SHOW TABLES;")
                    tables = [table[0] for table in cursor.fetchall()]
                    self.stdout.write(self.style.NOTICE(f'Found {len(tables)} tables.'))

                    for table in tables:
                        try:
                            cursor.execute(f'DROP TABLE `{table}`;')
                            self.stdout.write(
                                self.style.SUCCESS(f'DROP table `{table}`.')
                            )
                        except OperationalError as oe:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'OperationalError dropping table `{table}`: {oe}.'
                                )
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Unexpected error dropping table `{table}`: {e}.'
                                )
                            )

                finally:
                    # Re-enable foreign key checks
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
                    self.stdout.write(self.style.NOTICE('Foreign key checks re-enabled.'))

        except OperationalError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error interacting with the database: {str(e)}"
                )
            )
            return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Unexpected error: {str(e)}"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS('Successfully dropped all tables.')
        )

        # Delete all keys in Redis
        try:
            delete_all_keys()
            self.stdout.write(
                self.style.SUCCESS('Successfully deleted all keys in Redis.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error deleting keys in Redis: {e}"
                )
            )
