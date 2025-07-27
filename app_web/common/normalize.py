import logging

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def get_normalized_email(email: str) -> str:
    try:
        email_name, domain_part = email.strip().lower().split('@', 1)
    except ValueError:
        logger.error(f"Invalid email address {email}")
        raise ValidationError('Invalid email address')

    # Handle Gmail addresses
    if domain_part in ['gmail.com', 'googlemail.com']:
        # Remove dots
        email_name = email_name.replace('.', '')
        # Remove anything after '+'
        email_name = email_name.split('+', 1)[0]

    # Handle iCloud addresses
    elif domain_part in ['icloud.com', 'me.com', 'mac.com']:
        email_name = email_name.split('+', 1)[0]

    # Handle Outlook/Hotmail addresses
    elif domain_part in ['outlook.com', 'hotmail.com', 'live.com']:
        email_name = email_name.split('+', 1)[0]

    # Handle Yahoo addresses
    elif domain_part.endswith('yahoo.com'):
        # Yahoo uses '-' for disposable addresses
        email_name = email_name.split('-', 1)[0]

    # Handle +1 in any email address
    elif email_name.endswith('+1'):
        email_name = email_name[:-2]

    # Reconstruct the normalized email
    normalized_email = f'{email_name}@{domain_part}'

    return normalized_email
