import logging

from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save

from app_api.models import API
from app_users.models import CustomUser
from app_contact.tasks import send_slack_message, send_zendesk_ticket


STATUS = (
	('IP', 'In Progress'),
	('CO', 'Completed'),
)

TYPE = (
	('SU', 'Support'),
	('SA', 'Sales'),
	('FE', 'Feedback'),
	('BI', 'Billing'),
)

logger = logging.getLogger(__name__)


class Contact(models.Model):
	user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, related_name='contacts',
		null=True, blank=True
	)
	support_user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, related_name='support_contacts',
		null=True, blank=True
	)
	api = models.ForeignKey(
		API,
		on_delete=models.DO_NOTHING,
		related_name='contacts',
		null=True,
		blank=True,
	)
	type = models.CharField(max_length=2, choices=TYPE, default='SU')
	name = models.CharField(max_length=100)
	email = models.EmailField()
	message = models.TextField()
	status = models.CharField(max_length=2, choices=STATUS, default='IP')
	zendesk_ticket_id = models.IntegerField(null=True, blank=True)
	slack_sent = models.BooleanField(
		default=False,
		help_text="Slack message sent to internal DoodleOps Support Channel."
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.name


@receiver(post_save, sender=Contact)
def send_slack_notification(sender, instance, created, **kwargs):
	"""
	Create two Celery tasks to send a Slack message and a zendesk ticket
	when a new Contact ticket is created.
	"""
	if created:

		type_name = dict(TYPE).get(instance.type)
		clean_datetime = instance.created_at.strftime("%Y-%m-%d %H:%M:%S")

		if instance.api:
			instance.message = (
				f"*API:* {instance.api.display_name}\n\n{instance.message}"
			)

		message = f"""
				*New Contact Ticket Created* - {clean_datetime}\n
				
				*Type:*     {type_name}\n
				*Email:*    {instance.email}\n
				*Link:*     {settings.EMAIL_DOMAIN_PATH}
							/admin/app_contact/contact/{instance.pk}/change/\n
				*Message:*  {instance.message}
				"""

		send_slack_message.delay(
			message={"text": message},
			contact_obj_pk=instance.pk
		)

		send_zendesk_ticket.delay(
			ticket_type=dict(TYPE).get(instance.type),
			body=instance.message,
			user_email=instance.email,
			user_name=instance.email,
			contact_obj_pk=instance.pk,
		)
