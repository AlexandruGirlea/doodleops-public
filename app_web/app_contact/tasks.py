import logging

import requests
from celery import shared_task
from django.conf import settings

from common.zendesk import create_zendesk_ticket

logger = logging.getLogger(__name__)


@shared_task()
def send_slack_message(message, contact_obj_pk=None):
    payload = message
    try:
        response = requests.post(settings.SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()

        if contact_obj_pk:
            from app_contact.models import Contact
            contact_obj = Contact.objects.get(pk=contact_obj_pk)
            contact_obj.slack_sent = True
            contact_obj.save()

    except requests.exceptions.RequestException as e:
        logger.error(f"Slack notification failed: {e}")


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def send_zendesk_ticket(
        self, ticket_type: str, body: str, contact_obj_pk=None,
        user_email: str = None, user_name: str = None
):
    ticker_id = create_zendesk_ticket(
        ticket_type=ticket_type, body=body,
        user_email=user_email, user_name=user_name
    )

    if contact_obj_pk:
        from app_contact.models import Contact
        contact_obj = Contact.objects.get(pk=contact_obj_pk)
        contact_obj.zendesk_ticket_id = ticker_id
        contact_obj.save()

    if not ticker_id:
        if self.request.retries >= self.max_retries:
            err_msg = (
                f"ZENDESK ERROR: \nFailed to create Zendesk ticket after"
                f" {self.max_retries} attempts."
            )
            logger.error(err_msg)
            send_slack_message.delay(message={"text": err_msg},)

        else:
            raise self.retry()

    return ticker_id
