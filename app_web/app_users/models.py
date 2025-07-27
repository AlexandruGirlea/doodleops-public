import uuid
import logging
from datetime import timedelta

import phonenumbers
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from oauth2_provider.models import AccessToken
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save, post_delete

from common.redis_logic.custom_redis import set_redis_key, delete_redis_key
from common.redis_logic.redis_schemas import (
	REDIS_KEY_USER_GENERATED_TOKEN, REDIS_OPENAI_OAUTH_USER_GENERATED_TOKEN,
)
from common.auth import generate_token
from app_settings.utils import get_setting
from app_users.validators import validate_phone_number

logger = logging.getLogger("APP_WEB_" + __name__)


class CustomUser(AbstractUser):
	email = models.EmailField(unique=True)
	normalized_email = models.EmailField(
		unique=False,
		help_text=(
			"This is a normalized version of the email field. "
			"It is used to check if the email is already in use and if we should "
			"provide credits to the user."
		),
		null=True, blank=True,
	)
	stripe_customer_id = models.CharField(max_length=100, unique=True)
	api_daily_call_limit = models.IntegerField(
		default=settings.DEFAULT_USER_API_DAILY_CALL_LIMIT
	)

	def save(self, *args, **kwargs):
		self.email = self.email.lower()
		super(CustomUser, self).save(*args, **kwargs)

	def __str__(self):
		return self.email


class PhoneNumbers(models.Model):
	# one to one user
	user = models.OneToOneField(
		CustomUser, on_delete=models.CASCADE, related_name="phone_number"
	)
	number = models.CharField(
		max_length=20, validators=[validate_phone_number], blank=True, null=True
	)
	is_validated = models.BooleanField(default=False)
	validation_code = models.CharField(max_length=6, blank=True, null=True)
	number_of_attempts = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def save(self, *args, **kwargs):
		if self.number:
			try:
				parsed_phone = phonenumbers.parse(self.number, None)
				self.number = phonenumbers.format_number(
					parsed_phone, phonenumbers.PhoneNumberFormat.E164
				)
			except phonenumbers.NumberParseException as e:
				logger.error(
					f"Invalid phone number format {self.number} with "
					f"error: {e}"
				)
				raise ValidationError("Invalid phone number format.")

		super(PhoneNumbers, self).save(*args, **kwargs)


class UserGeneratedToken(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
	description = models.CharField(max_length=255, blank=True, null=True)
	token = models.CharField(max_length=255, unique=True, blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		token_count = UserGeneratedToken.objects.filter(user=self.user).count()
		if token_count >= 10:
			raise ValidationError(message="Users can create at most 10 API keys.")
		self.token = generate_token()
		set_redis_key(
			REDIS_KEY_USER_GENERATED_TOKEN.format(token=self.token),
			simple_value=str(self.user.username),
		)
		super().save(*args, **kwargs)

	def delete(self, *args, **kwargs):
		delete_redis_key(REDIS_KEY_USER_GENERATED_TOKEN.format(token=self.token))
		super().delete(*args, **kwargs)


class AccountCreationIP(models.Model):
	ip_address = models.GenericIPAddressField(unique=True)
	account_count = models.PositiveIntegerField(default=1)
	first_attempt = models.DateTimeField(auto_now_add=True)

	def increment_count(self):
		self.account_count += 1
		self.save()

	def reset_count(self):
		self.account_count = 1
		self.first_attempt = timezone.now()
		self.save()

	def is_rate_limited(self):
		time_window_max_accounts_per_user_in_hours = get_setting(
			'time_window_max_accounts_per_user_in_hours',
			default=24,
			expected_type=int
		)
		max_accounts_per_user_in_time_window = get_setting(
			'max_accounts_per_user_in_time_window',
			default=5,
			expected_type=int
		)
		time_window = timedelta(hours=time_window_max_accounts_per_user_in_hours)

		if self.account_count >= max_accounts_per_user_in_time_window:
			if timezone.now() - self.first_attempt < time_window:
				return True
			else:
				self.reset_count()
				return False
		return False


class PasswordResetToken(models.Model):
	user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
	token = models.CharField(max_length=300, unique=True)
	used = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Token for {self.user.email} - Used: {self.used}"


@receiver(post_save, sender=AccessToken)
def store_access_token_in_redis(sender, instance, created, **kwargs):
	if created:
		set_redis_key(
			REDIS_OPENAI_OAUTH_USER_GENERATED_TOKEN.format(token=instance.token),
			simple_value=str(instance.user.username),
			expire=int((instance.expires - timezone.now()).total_seconds())
		)


@receiver(post_delete, sender=AccessToken)
def remove_access_token_from_redis(sender, instance, **kwargs):
	delete_redis_key(REDIS_OPENAI_OAUTH_USER_GENERATED_TOKEN.format(
		token=instance.token)
	)


@receiver(post_save, sender=CustomUser)
def create_phone_number(sender, instance, created, **kwargs):
	if created:
		PhoneNumbers.objects.create(user=instance)
