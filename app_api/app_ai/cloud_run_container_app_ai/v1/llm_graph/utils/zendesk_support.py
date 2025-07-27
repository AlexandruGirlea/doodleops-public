import os
import json
import logging
from typing import Union

import httpx
import requests

from core import settings

logger = logging.getLogger("APP_AI_V1_"+__name__)


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
    zendesk_ticket_groups = os.getenv("ZENDESK_TICKET_GROUPS")
    if zendesk_ticket_groups:
        return zendesk_ticket_groups

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

    zendesk_ticket_groups = (
        json.dumps({group['name']: group['id'] for group in group_list})
    )
    os.environ['ZENDESK_TICKET_GROUPS'] = zendesk_ticket_groups
    return zendesk_ticket_groups


def create_zendesk_ticket(
        ticket_type: str, body: str, user_email: str = None
) -> Union[str, None]:
    zendesk_ticket_groups = os.getenv("ZENDESK_TICKET_GROUPS")

    if not zendesk_ticket_groups:
        zendesk_ticket_groups = get_zendesk_ticket_groups()

    ticket_type = ticket_type.lower()
    settings_ticket_groups = zendesk_ticket_groups.lower()

    ticket_groups = json.loads(settings_ticket_groups)

    if ticket_type not in ticket_groups:
        logger.error(
            f"Invalid ticket type '{ticket_type}'. "
            f"Expected one of {list(ticket_groups.keys())}."
        )
        return None

    ticket_data = {
        'ticket': {
            'subject': f"Whatsapp Ticket {ticket_type}",
            'comment': {
                'body': body
            },
            'group_id': ticket_groups[ticket_type],
            'type': ticket_type,
            'priority': 'normal',
        }
    }

    if user_email:
        ticket_data['ticket']['requester'] = {
            'email': user_email,
            'name': user_email
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

        response_data = response.json()
        ticket_id = response_data.get('ticket', {}).get('id')
        return ticket_id

    except httpx.HTTPStatusError as http_err:
        logger.error(
            f"HTTP error occurred: {http_err} - Response: "
            f"{http_err.response.text}"
        )
    except Exception as err:
        logger.error(f"An error occurred: {err}")
    
    return None
