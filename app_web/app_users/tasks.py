import os
import time
import logging
from urllib.parse import urljoin

from twilio.rest import Client as TwilioClient
from celery import shared_task
from django.conf import settings
from oauth2_provider.models import clear_expired

from app_users.models import CustomUser
from app_settings.utils import get_setting
from app_contact.tasks import send_slack_message
from common.email_utils import send_email_via_ses
from common.date_time_utils import get_current_year

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def send_user_welcome_email_message(self, to_email: str, credits: int = None):
	try:
		email_base_html_logo_path = get_setting('email_base_html_logo_path')
		inline_images = (
			{"logo.png": email_base_html_logo_path}
			if os.path.exists(email_base_html_logo_path)
			else None
		)

		check_svg_path = "/app_web/static/check.png"
		if os.path.exists(check_svg_path):
			inline_images["check.png"] = check_svg_path

		send_email_via_ses(
			to_email=to_email, subject="👋 Hi! Welcome to DoodleOps",
			template_name='email/welcome_email.html',
			context={
				"inline_logo": inline_images,
				'email': to_email,
				'credits': credits,
				'current_year': get_current_year(),
				"domain_path": settings.EMAIL_DOMAIN_PATH,
				"api_docs_url": urljoin(settings.FASTAPI_HOST, "doc"),
				"terms_of_service_url": urljoin(
					settings.EMAIL_DOMAIN_PATH, "terms"
				),
				"privacy_policy_url": urljoin(
					settings.EMAIL_DOMAIN_PATH, "privacy"
				),
				"contact_url": urljoin(settings.EMAIL_DOMAIN_PATH, "contact")
			},
			inline_images=inline_images
		)
	except Exception as exc:
		logger.error(f"Attempt {self.request.retries + 1} failed: {exc}")

		# Check if maximum retries have been exceeded
		if self.request.retries >= self.max_retries:
			err_msg = (
				f"EMAIL ERROR: \nFailed to send email: {to_email} after"
				f" {self.max_retries} attempts."
			)
			logger.error(err_msg)
			send_slack_message.delay(message={"text": err_msg}, )

		else:
			# Retry the task
			raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def send_user_delete_email_message(self, to_email: str):
	try:
		email_base_html_logo_path = get_setting('email_base_html_logo_path')
		inline_images = (
			{"logo.png": email_base_html_logo_path}
			if os.path.exists(email_base_html_logo_path)
			else None
		)

		send_email_via_ses(
			to_email=to_email,
			subject="We're sorry to see you go",
			from_email=settings.DEFAULT_SUPPORT_EMAIL,
			template_name='email/delete_user_email.html',
			context={
				"inline_logo": inline_images,
				'email': to_email,
				'current_year': get_current_year(),
				"domain_path": settings.EMAIL_DOMAIN_PATH,
			},
			inline_images=inline_images
		)
	except Exception as exc:
		logger.error(f"Attempt {self.request.retries + 1} failed: {exc}")

		# Check if maximum retries have been exceeded
		if self.request.retries >= self.max_retries:
			err_msg = (
				f"EMAIL ERROR: \nFailed to send email: {to_email} after"
				f" {self.max_retries} attempts."
			)
			logger.error(err_msg)
			send_slack_message.delay(message={"text": err_msg}, )

		else:
			# Retry the task
			raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def send_user_emails_chunk(
		self, user_emails: list, subject: str, template_name: str,
		context: dict, from_email: str = None
):
	email_base_html_logo_path = get_setting('email_base_html_logo_path')

	inline_images = (
		{"logo.png": email_base_html_logo_path}
		if os.path.exists(email_base_html_logo_path)
		else None
	)

	try:
		for user_email in user_emails:
			context['email'] = user_email
			send_email_via_ses(
				to_email=user_email,
				subject=subject,
				from_email=from_email,
				template_name=template_name,
				context={"inline_logo": inline_images},
				inline_images=inline_images
			)
			time.sleep(0.5)  # to avoid rate limit
	except Exception as exc:
		logger.error(f"Attempt {self.request.retries + 1} failed: {exc}")

		if self.request.retries >= self.max_retries:
			err_msg = (
				f"EMAIL ERROR: \nFailed to send legal update email after"
				f" {self.max_retries} attempts."
			)
			logger.error(err_msg)
			send_slack_message.delay(message={"text": err_msg}, )
		else:
			raise self.retry(exc=exc)  # Retry the task


@shared_task(rate_limit='1/m')
def send_update_to_all_active_users(
		is_legal: bool = False, is_maintenance: bool = False
):
	if (is_legal and is_maintenance) or (not is_legal and not is_maintenance):
		err_msg = "Only one of is_legal or is_maintenance can be True."
		logger.error(err_msg)
		raise ValueError(err_msg)

	batch_size = 50
	qs = CustomUser.objects.filter(  # this is a generator
		is_active=True
	).values_list('email', flat=True).iterator(chunk_size=batch_size)

	if is_legal and not is_maintenance:
		subject = "We updated our terms of service and privacy policy",
		template_name = 'email/legal_update_email.html'
		context = {
			"current_year": get_current_year(),
			"domain_path": settings.EMAIL_DOMAIN_PATH,
		}
		from_email = settings.DEFAULT_SUPPORT_EMAIL
	else:
		subject = "Scheduled maintenance update"
		template_name = 'email/maintenance_update_email.html'
		context = {
			"current_year": get_current_year(),
			"domain_path": settings.EMAIL_DOMAIN_PATH,
			"maintenance_email_message": get_setting('maintenance_email_message'),
		}
		from_email = None

	chunk = []
	for email in qs:
		chunk.append(email)
		if len(chunk) >= batch_size:
			send_user_emails_chunk.delay(
				user_emails=chunk, subject=subject, template_name=template_name,
				context=context, from_email=from_email
			)
			chunk = []

	if chunk:  # Dispatch the last chunk if any
		send_user_emails_chunk.delay(
			user_emails=chunk, subject=subject, template_name=template_name,
			context=context, from_email=from_email
		)


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def send_user_validation_email(self, user_email: str, token: str):
	try:
		email_base_html_logo_path = get_setting('email_base_html_logo_path')
		inline_images = (
			{"logo.png": email_base_html_logo_path}
			if os.path.exists(email_base_html_logo_path)
			else None
		)

		send_email_via_ses(
			to_email=user_email,
			subject="Please confirm your email address",
			template_name='email/user_validation_email.html',
			context={
				"inline_logo": inline_images,
				'email': user_email,
				'link': (
					f"{settings.EMAIL_DOMAIN_PATH}/auth/validate-email/?{token}"
					),
				'current_year': get_current_year(),
				"domain_path": settings.EMAIL_DOMAIN_PATH,
			},
			inline_images=inline_images
		)
	except Exception as exc:
		logger.error(f"Attempt {self.request.retries + 1} failed: {exc}")

		if self.request.retries >= self.max_retries:
			err_msg = (
				f"EMAIL ERROR: \nFailed to send validation email to: {user_email} "
				f"after {self.max_retries} attempts."
			)
			logger.error(err_msg)
			send_slack_message.delay(message={"text": err_msg}, )
		else:
			raise self.retry(exc=exc)  # Retry the task


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def send_user_reset_password_email(self, user_email: str, token: str):
	try:
		email_base_html_logo_path = get_setting('email_base_html_logo_path')
		inline_images = (
			{"logo.png": email_base_html_logo_path}
			if os.path.exists(email_base_html_logo_path)
			else None
		)

		send_email_via_ses(
			to_email=user_email,
			subject="Follow this link to reset your password",
			template_name='email/reset_password_email.html',
			context={
				"inline_logo": inline_images,
				'email': user_email,
				'link': (
					f"{settings.EMAIL_DOMAIN_PATH}/auth/password-reset/?{token}"
					),
				'current_year': get_current_year(),
				"domain_path": settings.EMAIL_DOMAIN_PATH,
			},
			inline_images=inline_images
		)
	except Exception as exc:
		logger.error(f"Attempt {self.request.retries + 1} failed: {exc}")

		if self.request.retries >= self.max_retries:
			err_msg = (
				f"EMAIL ERROR: \nFailed to send reset password email to: "
				f"{user_email} after {self.max_retries} attempts."
			)
			logger.error(err_msg)
			send_slack_message.delay(message={"text": err_msg}, )
		else:
			raise self.retry(exc=exc)  # Retry the task


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def send_user_test_email(self):
	user_email = "alex@doodleops.com"

	try:
		email_base_html_logo_path = get_setting('email_base_html_logo_path')
		inline_images = (
			{"logo.png": email_base_html_logo_path}
			if os.path.exists(email_base_html_logo_path)
			else None
		)

		send_email_via_ses(
			to_email=user_email,
			subject="Test email",
			template_name='email/test_email.html',
			context={
				"inline_logo": inline_images,
				'email': user_email,
				'current_year': get_current_year(),
				"domain_path": settings.EMAIL_DOMAIN_PATH,
			},
			inline_images=inline_images
		)
	except Exception as exc:
		logger.error(f"Attempt {self.request.retries + 1} failed: {exc}")

		if self.request.retries >= self.max_retries:
			err_msg = (
				f"EMAIL ERROR: \nFailed to send test email to: {user_email} after"
				f" {self.max_retries} attempts."
			)
			logger.error(err_msg)
			send_slack_message.delay(message={"text": err_msg}, )
		else:
			raise self.retry(exc=exc)


@shared_task
def clear_oauth2_tokens():
	try:
		clear_expired()
	except:
		logger.error(
			"Could not clear expired oAuth tokens. Cron job does not work"
		)


def send_user_sms_to_validate_phone_number(
		to_phone_number: str, verification_code: str
) -> bool:
	"""
	Sends an SMS containing a verification code to the specified phone number
	using Twilio.
	"""
	try:
		# Initialize the Twilio client with your account SID and auth token
		client = TwilioClient(
			settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
		)

		# Construct the SMS message
		message = client.messages.create(
			body=f"DoodleOps code: {verification_code}",
			from_=settings.TWILIO_PHONE_NUMBER,  # Your Twilio verified phone number
			to=to_phone_number
		)

		logger.info(
			f"Sent SMS to {to_phone_number} with verification code {verification_code}. "
			f"Message body response: {message.body}"
		)

		return True
	except Exception as e:
		logger.error(
			f"Failed to send SMS to {to_phone_number} with verification code "
			f"{verification_code}. Error: {e}"
		)
		return False
