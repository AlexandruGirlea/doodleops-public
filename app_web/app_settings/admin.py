import logging
from django.contrib import admin

from app_settings.models import Setting


logger = logging.getLogger(__name__)


class SettingAdmin(admin.ModelAdmin):
	list_display = ('key', 'value_type', 'get_value_display', 'description')

	def get_value_display(self, obj):
		return obj.get_value()

	get_value_display.short_description = 'Value'

	def has_add_permission(self, request):
		return request.user.is_superuser

	def has_change_permission(self, request, obj=None):
		return request.user.is_superuser

	def has_delete_permission(self, request, obj=None):
		return False


admin.site.register(Setting, SettingAdmin)
