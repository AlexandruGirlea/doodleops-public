from django.db import models

from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save

from app_users.models import CustomUser
from app_contact.tasks import send_slack_message, send_zendesk_ticket


class SuggestNewFeature(models.Model):
	user = models.ForeignKey(
		CustomUser, on_delete=models.CASCADE, related_name='suggested_features',
		null=False, blank=False
	)
	feature_description = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.user.email}"


@receiver(post_save, sender=SuggestNewFeature)
def send_slack_notification(sender, instance, created, **kwargs):
	"""
	Create two Celery tasks to send a Slack message and a zendesk ticket
	when a new SuggestNewFeature object is created
	"""
	if created:

		msg_type = "Feature Suggestion"
		clean_datetime = instance.created_at.strftime("%Y-%m-%d %H:%M:%S")

		message = f"""
				*New Feature Suggestion Ticket Created* - {clean_datetime}\n

				*Type:*     {msg_type}\n
				*Email:*    {instance.user.email}\n
				*Link:*     {settings.EMAIL_DOMAIN_PATH}
							/admin/app_pages/suggestnewfeature/{instance.pk}/change/\n
				*Message:*  {instance.feature_description}
				"""

		send_slack_message.delay(message={"text": message})

		send_zendesk_ticket.delay(
			ticket_type=msg_type,
			body=instance.feature_description,
			user_email=instance.user.email,
			user_name=instance.user.email,
		)


class BlogCategory(models.Model):
	name = models.CharField(max_length=255, unique=True)
	display_order = models.IntegerField(default=0, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.name}"


class BlogPost(models.Model):
	category = models.ForeignKey(
		BlogCategory, on_delete=models.CASCADE, related_name='blog_posts',
		null=False, blank=False
	)
	title = models.CharField(max_length=255, unique=True)
	description = models.TextField()
	blog_platform_url = models.URLField(unique=True)
	image_url = models.URLField()
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.title}"
