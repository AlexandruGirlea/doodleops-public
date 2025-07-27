"""
Limit customer to one active subscription
https://dashboard.stripe.com/settings/checkout
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from app_users.models import CustomUser
from app_settings.utils import get_setting
from common.redis_logic.custom_redis import set_redis_key
from common.redis_logic.redis_schemas import (
	ENTERPRISE_USER_MAX_CREDITS_LIMIT_PER_MONTH
)


User = get_user_model()


class PricingBuyCredit(models.Model):
	"""
	No Stripe metadata needed for this model.
	"""

	id = models.CharField(max_length=100, primary_key=True)  # Stripe Price ID
	name = models.CharField(max_length=100, unique=True)
	price_in_cents = models.IntegerField(default=0)
	credits = models.IntegerField(default=0)
	display_order = models.IntegerField(default=0)

	def __str__(self):
		return f"{self.name}"

	class Meta:
		verbose_name = "Stripe - Credit Plan"
		verbose_name_plural = "Stripe - Credit Plans"


class CustomerCreditsRemoved(models.Model):
	"""
	A model representing Customer Credits Removed by Admin / Staff.
	"""
	class RemovalType(models.TextChoices):
		BOUGHT = "bought"
		SUBSCRIPTION = "subscription"

	user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, related_name="user_credits_removed"
	)
	credits = models.IntegerField(
		default=0, help_text="Number of Credits removed."
	)
	created = models.DateTimeField(auto_now_add=True)
	backend_details = models.TextField(
		blank=True, null=True, help_text="This is not displayed to the user."
	)
	public_details = models.TextField(
		blank=True, null=True, help_text="This is displayed to the user."
		)
	removal_type = models.CharField(
		max_length=100, choices=RemovalType.choices, default=RemovalType.BOUGHT
	)

	last_updated_by = models.ForeignKey(
		CustomUser,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="credits_removed_last_updated_by"
	)

	def __str__(self):
		return f"{self.user.email} - {self.credits}"

	class Meta:
		verbose_name = "User - Credits Removed by Admin/Staff"
		verbose_name_plural = "Users - Credits Removed by Admin/Staff"


class CustomerCreditsBought(models.Model):
	"""
	A model representing Customer Credits Bought directly not from a subscription.
	"""

	user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, related_name="user_credits"
	)
	credits = models.IntegerField(default=0)
	created = models.DateTimeField(auto_now_add=True)
	expires = models.DateTimeField()
	details = models.TextField(
		blank=True, null=True, help_text="Details of the purchase."
	)

	def save(self, *args, **kwargs):
		if self.pk:
			raise ValidationError(
				"Updates are not allowed. You can only create or delete records."
			)
		self.expires = timezone.now() + timedelta(
			days=get_setting(key="credits_expire_days", default=90)
		)
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.user.email} - {self.credits}"

	class Meta:
		verbose_name = "User - Credits Bought directly"
		verbose_name_plural = "Users - Credits Bought directly"


class CustomerCreditsBackup(models.Model):
	"""
	This is not currently used
	We should use this only for backing up Redis in case of a failure.
	"""

	redis_key = models.CharField(max_length=255, unique=True)
	redis_short_value = models.CharField(max_length=255, blank=True, null=True)
	redis_long_value = models.TextField(blank=True, null=True)
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Backup - Customer Credits"
		verbose_name_plural = "Backups - Customer Credits"


class PricingBuySubscription(models.Model):
	"""
	A model representing a Pricing Plan API Units.

	Necessary Stripe metadata:
	- api_daily_call_limit

	Daily call limit is used for limiting requests per seconds
	Daily call limit is not used for determining the monthly call limit

	`api_daily_call_limit` is used for limiting requests per seconds and
	represents the number of API calls / day a user can make.
	"""

	id = models.CharField(max_length=100, primary_key=True)  # Stripe Price ID
	name = models.CharField(max_length=100)
	price_in_cents = models.IntegerField(blank=True, null=True)
	credits_monthly = models.IntegerField(blank=True, null=True)
	is_monthly = models.BooleanField(default=False)
	is_yearly = models.BooleanField(default=False)
	display_order = models.IntegerField(default=0)
	api_daily_call_limit = models.IntegerField(
		default=0,
		help_text=(
			"This is used to set new user daily call limit based on the "
			"subscription plan they purchased. If the subscription is canceled, "
			"the user will be downgraded to the default daily call limit, "
			"set in the Settings model."
		)
	)
	is_metered = models.BooleanField(
		default=False, help_text="This is the Enterprise plan."
	)

	def __str__(self):
		if self.is_monthly:
			return f"{self.name} - monthly"
		elif self.is_yearly:
			return f"{self.name} - yearly"
		return f"{self.name}"

	class Meta:
		verbose_name = "Stripe - Subscription Plan"
		verbose_name_plural = "Stripe - Subscription Plans"


class PricingBuySubscriptionTier(models.Model):
	"""
	`start` and `end` values represent the number of Credits a user used
	and `price_in_cents` represents the price for the Credits used, with
	a minimum of `flat_amount_in_cents`.
	"""

	start = models.IntegerField(help_text="No of Credits consumed Start")
	end = models.IntegerField(  # null for unlimited
		null=True, blank=True, help_text="No of Credits consumed End"
	)
	price_in_cents = models.DecimalField(
		max_digits=10, decimal_places=2, default=0.00,
		help_text="Price in cents per Credit used."
	)
	flat_amount_in_cents = models.IntegerField(default=0)
	pricing_plan = models.ForeignKey(
		PricingBuySubscription,
		on_delete=models.CASCADE,
		related_name="pricing_plan_tiers",
	)

	class Meta:
		verbose_name = "Stripe - Subscription Tier"
		verbose_name_plural = "Stripe - Subscription Tiers"


class StripeSubscriptionItem(models.Model):
	"""
	A model representing a Stripe Subscription Item

	We need to display and know how much did the user use in the current month,
	so we can deduce that from APICounter + redis logs of the current day
	based on that we can calculate:
	- monthly cost for metered subscribed users
	- remaining API calls for the current month for the rest of subscribed users
	"""

	id = models.CharField(max_length=100, primary_key=True)
	subscription_id = models.CharField(max_length=100)
	user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	pricing_plan = models.ForeignKey(
		PricingBuySubscription,
		on_delete=models.DO_NOTHING,
	)
	current_period_start = models.IntegerField(null=True, blank=True)
	start_date = models.DateField(null=True, blank=True)

	current_period_end = models.IntegerField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)

	cancel_at_period_end = models.BooleanField(default=False)
	is_active = models.BooleanField(default=False)
	is_past_due = models.BooleanField(default=False)
	is_deleted = models.BooleanField(default=False)

	event_id = models.CharField(max_length=100, null=True, blank=True)
	last_updated = models.DateTimeField(
		null=True, blank=True, help_text=(
			"This is used to keep a record and to determine who should get "
			"monthly credits for the yearly subscription. Task name: "
			"task_add_monthly_credits_to_yearly_subscriptions"
		)
	)

	class Meta:
		indexes = [models.Index(fields=["id"])]
		verbose_name = "Stripe - Subscription Item"
		verbose_name_plural = "Stripe - Subscription Items"

	def __str__(self):
		return f"{self.id} - {self.pricing_plan.name}"

	def save(self, *args, **kwargs):
		self.last_updated = timezone.now()
		super().save(*args, **kwargs)


class StripeEvent(models.Model):
	"""
	A model representing a Stripe Event
	"""

	id = models.CharField(max_length=100, primary_key=True)
	user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, null=True, blank=True
	)
	event_type = models.CharField(max_length=100)
	event_object = models.TextField()
	created = models.DateTimeField(auto_now_add=True)
	error = models.CharField(max_length=255, null=True, blank=True)

	class Meta:
		indexes = [models.Index(fields=["event_type", "id"])]
		verbose_name = "Stripe - Event"
		verbose_name_plural = "Stripe - Events"

	def __str__(self):
		if self.user:
			return f"{self.user.email} - {self.event_type}"
		return f"{self.id} - {self.event_type}"


class StripeInvoice(models.Model):
	"""
	Stripe Invoices are used only for subscription payments.
	When a Subscription Item is created, the invoice is created first => the
	Subscription Item Object does not exist yet.
	"""

	STATUS_CHOICES = [
		("open", "Open"),
		("draft", "Draft"),
		("paid", "Paid"),
		("payment_failed", "Payment failed"),
	]
	id = models.CharField(max_length=100, primary_key=True)
	event_id = models.CharField(max_length=100, null=True, blank=True)
	created = models.IntegerField()
	user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, null=True, blank=True
	)
	price = models.ForeignKey(
		PricingBuySubscription,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)
	subscription_item = models.ForeignKey(
		StripeSubscriptionItem,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)
	amount_due = models.IntegerField(help_text="Amount due in cents")
	status = models.CharField(
		max_length=20,
		choices=STATUS_CHOICES,
		default="unpaid",
	)

	class Meta:
		verbose_name = "Stripe - Invoice"
		verbose_name_plural = "Stripe - Invoices"


class StripePaymentIntent(models.Model):
	"""
	If we have an invoice object, then it's a subscription payment.
	If not, then it's a one-time payment to buy credits.
	We only created objects for status succeeded, the rest are stored as events.
	"""

	STATUS_CHOICES = [("succeeded", "Succeeded")]

	id = models.CharField(max_length=100, primary_key=True)
	event_id = models.CharField(max_length=100, null=True, blank=True)
	created = models.IntegerField()
	user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, null=True, blank=True
	)
	invoice = models.ForeignKey(
		StripeInvoice, on_delete=models.SET_NULL, null=True, blank=True
	)
	amount = models.IntegerField(help_text="Amount in cents")
	status = models.CharField(
		max_length=23,
		choices=STATUS_CHOICES,
		default="unpaid",
	)

	class Meta:
		indexes = [models.Index(fields=["id"])]
		verbose_name = "Stripe - Payment Intent"
		verbose_name_plural = "Stripe - Payment Intents"

	def __str__(self):
		if self.user:
			return f"{self.user.email} - {self.id}"
		return f"{self.id}"


class CustomUserFinancials(User):
	"""
	A proxy model to present 'CustomUser' from a financial/credits perspective
	in the Django admin.
	This shares the same underlying table as CustomUser,
	but can be registered separately under a different admin.
	"""
	class Meta:
		proxy = True
		verbose_name = "User - Financial Info"
		verbose_name_plural = "Users - Financials Info"

	def __str__(self):
		return self.email


class EnterpriseUser(models.Model):
	"""Only Enterprise users can access the Enterprise Subscription"""
	user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	max_credits_limit_per_month = models.IntegerField(default=5000)
	details = models.TextField(blank=True, null=True)
	last_updated_by = models.ForeignKey(
		CustomUser,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="enterpriseuser_last_updated"
	)
	
	def save(self, *args, **kwargs):
		set_redis_key(
			key=ENTERPRISE_USER_MAX_CREDITS_LIMIT_PER_MONTH.format(
				username=self.user.username),
			simple_value=str(self.max_credits_limit_per_month),
		)
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.user.email}"

	class Meta:
		verbose_name = "User - is Enterprise "
		verbose_name_plural = "Users - are Enterprise"
