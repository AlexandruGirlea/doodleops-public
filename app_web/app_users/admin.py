from django.urls import path
from django.shortcuts import redirect
from django.utils.html import mark_safe
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.core.exceptions import ValidationError

from app_users.models import CustomUser, UserGeneratedToken, PhoneNumbers
from app_users.tasks import send_update_to_all_active_users


class AdminUser(DefaultUserAdmin):
	change_list_template = "admin/custom_user_change_list.html"

	list_display = (
		"email",
		"stripe_customer_id",
		"username",
		"is_superuser",
		"is_staff",
		"is_active",
		"date_joined",
	)
	readonly_fields = (
		"username", "date_joined", "last_login", "password", "stripe_customer_id"
	)

	# This sets what fields are displayed in the change view
	fieldsets = (
		(None, {"fields": ("username", "password")}),
		(
			"Personal info",
			{
				"fields": (
					"first_name",
					"last_name",
					"email",
					"normalized_email",
					"stripe_customer_id",
					"api_daily_call_limit",
				)
			},
		),
		(
			"Permissions",
			{
				"fields": (
					"is_active",
					"is_staff",
					"is_superuser",
				)
			},
		),
		("Important dates", {"fields": ("last_login", "date_joined")}),
		# add group
		("Groups", {"fields": ("groups",)}),
	)

	# Adds a password change link next to the password field
	def password(self, obj):
		return mark_safe(f'<a href="password/">Change password</a>')

	def get_urls(self):
		urls = super().get_urls()
		custom_urls = [
			path(
				'send-update-to-all-users/',
				self.admin_site.admin_view(self.send_update_to_all_users_by_type),
				name='send_update_to_all_users'
			),
		]
		return custom_urls + urls

	def send_update_to_all_users_by_type(self, request):
		update_type = request.GET.get("type")
		if not update_type or update_type not in {"legal", "maintenance"}:
			self.message_user(
				request,
				"Invalid type. Please provide a valid type "
				"(legal or maintenance)",
				messages.ERROR
			)
			return redirect("..")
		if request.method == "POST" and request.user.is_superuser:
			send_update_to_all_active_users.delay(
				is_legal=update_type == "legal",
				is_maintenance=update_type == "maintenance"
			)

			if update_type == "legal":
				msg = "Legal update emails are being sent to all active users."
			else:
				msg = (
					"Maintenance update emails are being sent to all active "
					"users."
					)

			self.message_user(request, msg, messages.SUCCESS)
		return redirect("..")


class AdminUserGeneratedToken(admin.ModelAdmin):
	list_display = ("user_email", "description", "token", "created_at")
	readonly_fields = ("token", "created_at")

	def save_model(self, request, obj, form, change):
		if change:
			raise ValidationError("Updating UserGeneratedToken is not allowed.")
		super().save_model(request, obj, form, change)

	def user_email(self, obj):
		return obj.user.email

	user_email.short_description = "User Email"


class AdminPhoneNumbers(admin.ModelAdmin):
	list_display = (
		"user_email",
		"number",
		"is_validated",
		"validation_code",
		"number_of_attempts",
		"created_at",
		"updated_at",
	)
	readonly_fields = ("created_at", "updated_at")

	def user_email(self, obj):
		return obj.user.email

	user_email.short_description = "User Email"


admin.site.register(CustomUser, AdminUser)
admin.site.register(UserGeneratedToken, AdminUserGeneratedToken)
admin.site.register(PhoneNumbers, AdminPhoneNumbers)
