from django import forms
from django.contrib import admin
from django.urls import reverse
from django.http import Http404
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from app_financial.admin_forms import (
	StripeEventAdminForm, CustomerCreditsRemovedForm
)
from app_financial.models import (
	PricingBuyCredit,
	CustomerCreditsBought,
	PricingBuySubscription,
	StripeSubscriptionItem,
	StripeInvoice,
	StripePaymentIntent,
	StripeEvent,
	PricingBuySubscriptionTier,
	CustomUserFinancials,
	CustomerCreditsRemoved,
	EnterpriseUser
)
from common.date_time_utils import (
	ADMIN_CREATED_FORMAT,
	convert_timestamp_to_datetime,
)
from common.redis_logic.redis_utils import (
	get_remaining_credits_bought,
	get_remaining_monthly_subscription_credits,
	remove_credits_bought_directly,
	remove_credits_bought_using_subscription
)
from common.redis_logic.redis_utils import (
	add_one_time_credits_to_customer,
	get_instant_cost_in_dollars_for_metered_subscription
)


class PricingBuyCreditAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"id",
		"credits",
	)


class CustomerCreditsBoughtAdmin(admin.ModelAdmin):
	autocomplete_fields = ['user']
	list_display = ("id", "user", "credits", "created", "expires", "details")
	search_fields = ("user__email", "user__id", "details")

	readonly_fields = ("credits", "expires")

	ordering = ("-created",)
	exclude = ('amount_in_cents',)

	def get_form(self, request, obj=None, **kwargs):
		form = super().get_form(request, obj, **kwargs)
		form.base_fields['amount_in_cents'] = forms.IntegerField(
			required=False, label="Amount in cents"
		)
		return form

	def save_model(self, request, obj, form, change):
		if change:
			raise ValidationError(
				"Updates are not allowed. You can only create or delete records."
			)
		if obj.credits < 0:
			raise ValidationError("Credits cannot be negative")

		amount_in_cents = form.cleaned_data.get('amount_in_cents', 0)

		add_one_time_credits_to_customer(
			user_obj=obj.user, amount_in_cents=amount_in_cents,
			details="Admin added credits." if not obj.details else obj.details,
			added_manually=True
		)

	def has_delete_permission(self, request, obj=None):
		return False

	# Remove the bulk delete action
	def get_actions(self, request):
		actions = super().get_actions(request)
		if 'delete_selected' in actions:
			del actions['delete_selected']
		return actions


class PricingBuySubscriptionAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"is_monthly",
		"is_yearly",
		"id",
		"api_daily_call_limit",
	)


class StripeSubscriptionItemAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"pricing_plan_name",
		"user",
		"created",
		"is_active",
		"is_past_due",
		"is_deleted",
	)
	search_fields = ("user__email", "id")

	# By default, everything is read-only
	readonly_fields = (
		"id",
		"pricing_plan_name",
		"user",
		"created",
		"is_active",
		"is_past_due",
		"is_deleted",
		"last_updated",
	)

	ordering = ("-created",)

	@staticmethod
	def pricing_plan_name(obj):
		if obj.pricing_plan:
			return obj.pricing_plan.name
		return None

	def get_readonly_fields(self, request, obj=None):
		# If user is superuser, allow editing is_active by removing it from
		# readonly_fields
		if request.user.is_superuser:
			return (
				"id",
				"pricing_plan_name",
				"user",
				"created",
				"is_past_due",
				"is_deleted",
			)
		# Otherwise, everything remains read-only
		return self.readonly_fields

	def has_change_permission(self, request, obj=None):
		# Only superusers can actually save changes
		if request.user.is_superuser:
			return True
		return False


class StripeEventAdmin(admin.ModelAdmin):
	form = StripeEventAdminForm

	list_display = ("id", "user", "event_type", "created_with_ms")
	ordering = ("-created",)

	search_fields = ("user__email", "id", "user__id")
	readonly_fields = ("user", "id", "created_with_ms", "error")

	def created_with_ms(self, obj):
		return obj.created.strftime(ADMIN_CREATED_FORMAT)

	created_with_ms.admin_order_field = "created"
	created_with_ms.short_description = "Created (with ms)"


class StripeInvoiceAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "created_with_ms", "status")
	search_fields = ("user__email", "id", "user__id")

	fieldsets = (
		(
			"Invoice",
			{
				"fields": (
					"id",
					"user",
					"price",
					"subscription_item",
					"amount_due",
					"status",
				)
			},
		),
	)
	readonly_fields = (
		"id",
		"created_with_ms",
		"event_obj",
		"amount_due",
		"status",
	)

	ordering = ("-created",)

	@staticmethod
	def event_obj(obj):
		if obj.event_id:
			try:
				event = StripeEvent.objects.get(id=obj.event_id)
				url = reverse(
					"admin:app_financial_stripeevent_change", args=(event.pk,)
				)
				return format_html('<a href="{}">{}</a>', url, event.pk)
			except StripeEvent.DoesNotExist:
				pass
		return obj.event_id

	def created_with_ms(self, obj):
		"""ms = milliseconds"""
		return convert_timestamp_to_datetime(obj.created).strftime(
			ADMIN_CREATED_FORMAT
		)

		# Allows column order sorting

	created_with_ms.admin_order_field = "created"
	# Sets column header
	created_with_ms.short_description = "Created (with ms)"

	def has_change_permission(self, request, obj=None):
		return False

	def has_add_permission(self, request):
		return False


class StripePaymentIntentAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "created")
	search_fields = ("user__email", "id", "user__id")
	readonly_fields = ("user", "id", "created")

	ordering = ("-created",)


class PricingBuySubscriptionTierAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"start",
		"end",
		"price_in_cents",
		"pricing_plan",
	)

	ordering = ("start",)


class UserFinancialsAdmin(DefaultUserAdmin):
	"""
	We inherit from UserAdmin so that we keep the normal functionality
	of Django's built-in User admin, plus add our custom view.
	"""
	change_form_template = "admin/app_financial/user_financials.html"
	list_display = (
		"email", "normalized_email", "username", "stripe_customer_id",
		"api_daily_call_limit"
	)

	def changeform_view(
			self, request, object_id, form_url='', extra_context=None
	):
		user = self.get_object(request, object_id)
		if not user:
			raise Http404("User not found.")

		username = user.username

		remaining_credits_bought_dict = get_remaining_credits_bought(username)
		extra_context = {
			"remaining_credits_bought": sum(
				remaining_credits_bought_dict.values()
			),
			"remaining_monthly_subscription_credits": (
				get_remaining_monthly_subscription_credits(username)
			),
		}
		extra_context["total_credits"] = (
			extra_context["remaining_credits_bought"]
			+ extra_context["remaining_monthly_subscription_credits"]
		)

		if extra_context.get("remaining_credits_bought"):
			remaining_credits_bought_obj = (
				CustomerCreditsBought.objects.filter(
					pk__in=remaining_credits_bought_dict.keys()
				).order_by("-pk")
			)
			remaining_credits_bought_details = {}
			for obj_credits in remaining_credits_bought_obj:
				remaining_credits_bought_details[obj_credits.id] = {
					"credits_bought": obj_credits.credits,
					"credits_remaining": (
						remaining_credits_bought_dict[obj_credits.id]
					),
					"created": obj_credits.created.strftime(
						"%d-%m-%Y, %H:%M:%S"
					),
					"expires": obj_credits.expires.strftime(
						"%d-%m-%Y, %H:%M:%S"
					),
				}

			extra_context["remaining_credits_bought_details"] = (
				remaining_credits_bought_details
			)

		try:
			stripe_subs_items = StripeSubscriptionItem.objects.filter(user=user)
		except ObjectDoesNotExist:
			return super().changeform_view(
				request, object_id, form_url, extra_context
			)
		except MultipleObjectsReturned:
			raise Http404(
				"Multiple StripeSubscriptionItem objects found for this user."
			)

		extra_context["stripe_subs_items"] = []
		for stripe_subs_item in stripe_subs_items:
			stripe_subs_item_obj = {
				"subscription_id": stripe_subs_item.subscription_id,
				"created": stripe_subs_item.created.strftime(
					"%d-%m-%Y, %H:%M:%S"
				),
				"pricing_plan": (
					stripe_subs_item.pricing_plan.name +
					" - Monthly"
					if stripe_subs_item.pricing_plan.is_monthly else
					" - Yearly"
				),
				"start_date": stripe_subs_item.start_date.strftime(
					"%d-%m-%Y, %H:%M:%S"
				),
				"end_date": stripe_subs_item.end_date.strftime(
					"%d-%m-%Y, %H:%M:%S"
				),
				"cancel_at_period_end": stripe_subs_item.cancel_at_period_end,
				"is_active": stripe_subs_item.is_active,
				"is_past_due": stripe_subs_item.is_past_due,
				"is_deleted": stripe_subs_item.is_deleted,
				"event_id": stripe_subs_item.event_id,
				"cost_for_metered_subscription": None
			}

			if stripe_subs_item.pricing_plan.is_metered:
				stripe_subs_item_obj["cost_for_metered_subscription"] = (
					get_instant_cost_in_dollars_for_metered_subscription(
						stripe_subs_item
					)
				)

			extra_context["stripe_subs_items"].append(stripe_subs_item_obj)

		extra_context["user_change_url"] = reverse(
			"admin:app_users_customuser_change", args=(object_id,)
		)

		extra_context["admin_url_name_list"] = reverse(
			"admin:app_financial_customuserfinancials_changelist"
		)

		return super().changeform_view(
			request=request, object_id=object_id, form_url=form_url,
			extra_context=extra_context
		)


class CustomerCreditsRemovedAdmin(admin.ModelAdmin):
	form = CustomerCreditsRemovedForm
	autocomplete_fields = ['user']
	list_display = ("id", "user", "credits", "created", "last_updated_by")
	search_fields = ("user__email",)
	readonly_fields = ("created", "last_updated_by")
	ordering = ("-created",)

	def save_model(self, request, obj, form, change):
		"""
		The CustomerCreditsRemovedForm checks if user has enough credits to remove
		"""
		if change:
			raise ValidationError(
				"Updates are not allowed. You can only create or delete records."
			)
		obj.last_updated_by = request.user
		# check if credits is not negative raise error
		if obj.credits < 0:
			raise ValidationError("Credits cannot be negative")

		if obj.removal_type == "bought":
			remove_credits_bought_directly(
				username=obj.user.username, no_of_credits=obj.credits
			)
			obj.save()

		elif obj.removal_type == "subscription":
			remove_credits_bought_using_subscription(
				username=obj.user.username, no_of_credits=obj.credits
			)
			obj.save()

	def has_delete_permission(self, request, obj=None):
		return False

	# Remove the bulk delete action
	def get_actions(self, request):
		actions = super().get_actions(request)
		if 'delete_selected' in actions:
			del actions['delete_selected']
		return actions


class EnterpriseUserAdmin(admin.ModelAdmin):
	autocomplete_fields = ['user']
	search_fields = ("user__email",)
	list_display = ("user", "last_updated_by", "created_at")
	readonly_fields = ("updated_at", "created_at", "last_updated_by")

	def save_model(self, request, obj, form, change):
		# Set the last_updated_by to the current user before saving
		obj.last_updated_by = request.user
		super().save_model(request, obj, form, change)


admin.site.register(PricingBuyCredit, PricingBuyCreditAdmin)
admin.site.register(CustomerCreditsBought, CustomerCreditsBoughtAdmin)
admin.site.register(PricingBuySubscription, PricingBuySubscriptionAdmin)
admin.site.register(StripeSubscriptionItem, StripeSubscriptionItemAdmin)
admin.site.register(StripeEvent, StripeEventAdmin)
admin.site.register(StripeInvoice, StripeInvoiceAdmin)
admin.site.register(StripePaymentIntent, StripePaymentIntentAdmin)
admin.site.register(PricingBuySubscriptionTier, PricingBuySubscriptionTierAdmin)
admin.site.register(CustomUserFinancials, UserFinancialsAdmin)
admin.site.register(CustomerCreditsRemoved, CustomerCreditsRemovedAdmin)
admin.site.register(EnterpriseUser, EnterpriseUserAdmin)
