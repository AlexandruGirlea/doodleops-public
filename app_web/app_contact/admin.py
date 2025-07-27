from django.contrib import admin
from django.utils import timezone

from app_contact.models import Contact


class ContactAdmin(admin.ModelAdmin):
	list_display = (
		'created_at', 'email', 'type', 'support_user', 'updated_at',
		'slack_sent', 'zendesk_ticket_id', 'status'
	)
	search_fields = ('email', 'type', 'created_at', 'support_user', 'status')
	readonly_fields = (
		'created_at', 'name', 'email', 'message', 'user', 'support_user', 'type',
		'api', 'slack_sent', 'zendesk_ticket_id'
	)
	ordering = ('-created_at',)

	def has_add_permission(self, request):
		return False

	def has_delete_permission(self, request, obj=None):
		return False

	# has change permission only for status field not for other fields
	def has_change_permission(self, request, obj=None):
		if obj is not None and obj.status == 'IP':
			return True
		return False

	def get_actions(self, request):
		"""
		Disable bulk delete_selected action
		"""
		actions = super().get_actions(request)
		if 'delete_selected' in actions:
			del actions['delete_selected']
		return actions

	def save_model(self, request, obj, form, change):
		if change:
			old_obj = Contact.objects.get(pk=obj.pk)
			if old_obj.status != obj.status:
				obj.support_user = request.user
				obj.updated_at = timezone.now()
		super().save_model(request, obj, form, change)


admin.site.register(Contact, ContactAdmin)
