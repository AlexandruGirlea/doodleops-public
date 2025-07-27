import logging
import datetime

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError

from app_settings.models import Setting
from app_settings.defaults import DEFAULT_SETTINGS


logger = logging.getLogger(__name__)


TYPE_MAPPING = {
    int: 'int',
    str: 'str',
    bool: 'bool',
    float: 'float',
    datetime.datetime: 'datetime',
    dict: 'json',
}


class Command(BaseCommand):
    help = 'Populate default application settings'

    @staticmethod
    def populate_settings():
        for key, setting in DEFAULT_SETTINGS.items():
            value = setting['value']
            description = setting['description']
            setting_type = setting['type']

            # Map Python type to model's value_type
            value_type = TYPE_MAPPING.get(setting_type)
            if not value_type:
                logger.error(f"Unsupported type {setting_type} for key '{key}'")
                raise ValueError(
                    f"Unsupported type {setting_type} for key '{key}'"
                )

            # Initialize all value fields to None
            value_fields = {
                'int_value': None,
                'str_value': None,
                'bool_value': None,
                'float_value': None,
                'datetime_value': None,
                'json_value': None,
            }

            # Set the appropriate value field
            value_field_name = f'{value_type}_value'
            value_fields[value_field_name] = value

            # if Setting exists, skip
            if Setting.objects.filter(key=key).exists():
                print(f"Setting '{key}' already exists. Skipping...")
                continue

            # Create the Setting instance
            setting_instance = Setting(
                key=key,
                value_type=value_type,
                description=description,
                **value_fields
            )

            try:
                setting_instance.full_clean()  # This calls the clean() method
                setting_instance.save()
            except ValidationError as e:
                logger.error(f"Error creating setting '{key}': {e}")
                print(f"Error creating setting '{key}': {e}")

    def handle(self, *args, **kwargs):
        self.populate_settings()
        self.stdout.write(self.style.SUCCESS("Settings have been created"))
