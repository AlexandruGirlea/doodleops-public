import json
import logging
from typing import Optional

import httpx
import requests
from django.conf import settings

from app_settings.utils import get_setting


logger = logging.getLogger(__name__)

ZENDESK_GROUP_SETTINGS_KEY = 'zendesk_ticket_groups'


def get_zendesk_ticket_groups() -> str:
    """
    This method is ment to be run manually to get the group IDs for the Zendesk
    tickets. We then use this to populate the app_settings/defaults.py file.

    This means that there is no need to handle exceptions here.

    Make sure that they are correlated with the Contact TYPES.

    Format that we use:
    "zendesk_ticket_groups": {
        "value": '{"Billing": 29255862532753, "Feedback": 29258048961809, '
                 '"Sales": 29255902490001, "Support": 29203569010961}',
        "type": str,
        "description": "Ex: `1-2` this is in business days.",
    }

    Example how to use it:
    python manage.py shell

    from common.zendesk import get_zendesk_ticket_groups
    get_zendesk_ticket_groups()
    """
    response = requests.get(
        url=f'https://{settings.ZENDESK_SUBDOMAIN}/api/v2/groups.json',
        auth=(
            f'{settings.ZENDESK_USER_EMAIL}/token',
            settings.ZENDESK_API_TOKEN
        ),
        headers={
                    'Content-Type': 'application/json'
                }
    )
    response.raise_for_status()
    data = response.json()
    group_list = data['groups']

    return json.dumps({group['name']: group['id'] for group in group_list})


def create_zendesk_ticket(
        ticket_type: str, body: str, user_email: str = None, user_name: str = None
) -> (Optional)[int]:
    settings_ticket_groups = get_setting(ZENDESK_GROUP_SETTINGS_KEY)

    if not settings_ticket_groups:
        logger.error(f"Setting {ZENDESK_GROUP_SETTINGS_KEY} not found.")
        return

    ticket_type = ticket_type.lower()
    settings_ticket_groups = settings_ticket_groups.lower()

    ticket_groups = json.loads(settings_ticket_groups)

    if ticket_type not in ticket_groups:
        logger.error(
            f"Invalid ticket type '{ticket_type}'. "
            f"Expected one of {list(ticket_groups.keys())}."
        )
        return

    ticket_data = {
        'ticket': {
            'subject': f"Ticket {ticket_type}",
            'comment': {
                'body': body
            },
            'group_id': ticket_groups[ticket_type],
            'type': ticket_type,
            'priority': (
                'normal' if ticket_type in {'support', 'feedback'} else 'high'
            ),
        }
    }

    if user_email:
        ticket_data['ticket']['requester'] = {
            'email': user_email,
            'name': user_name if user_name else user_email
        }

    try:
        response = httpx.post(
            url=f'https://{settings.ZENDESK_SUBDOMAIN}/api/v2/tickets.json',
            json=ticket_data,
            auth=(
                    f'{settings.ZENDESK_USER_EMAIL}/token',
                    settings.ZENDESK_API_TOKEN
                ),
            headers={
                'Content-Type': 'application/json',
            }
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as http_err:
        logger.error(
            f"HTTP error occurred: {http_err} - Response: "
            f"{http_err.response.text}"
        )
        return
    except Exception as err:
        logger.error(f"An error occurred: {err}")
        return

    response_data = response.json()
    ticket_id = response_data.get('ticket', {}).get('id')

    if ticket_id and isinstance(ticket_id, int):
        logger.info(f"Successfully created ticket with ID: {ticket_id}")
        return ticket_id

    logger.error("Failed to retrieve ticket ID from the response.")
    return
