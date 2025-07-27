import json
import random
import string
import logging
from typing import Literal

from app_settings.utils import get_setting

logger = logging.getLogger(__name__)


DEFAULT_API_DAILY_CALL_LIMIT = get_setting(
    "default_user_api_daily_call_limit",
    default=100,
)


def chunked(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    for i in range(0, len(iterable), n):
        yield iterable[i: i + n]


def convert_cents_into_credit(
        amount_in_cents: int,
        credit_type: Literal["one_time", "monthly", "yearly"],
        added_manually: bool = False
) -> int:
    """
    This function will convert a given amount in cents into a credit amount.
    In production, this is only used for credit_type=one_time.
    `added_manually` is for credits added from Admin dashboard.
    """
    cents_to_credit_ratio = get_setting(
        "cents_to_credit_ratio",
        default=1,
        expected_type=float,
    )

    if credit_type == "monthly":
        value = int(amount_in_cents / cents_to_credit_ratio * 1.1)
        logger.info(
            f"Converting {amount_in_cents} cents into monthly credits. "
            "Formula: `amount_in_cents / cents_to_credit_ratio * 1.1`. "
            f"Cents to credit ratio: {cents_to_credit_ratio}. "
            f"Converted value: {value}."
        )
        return value
    elif credit_type == "yearly":
        value = int(amount_in_cents / cents_to_credit_ratio / 10 * 1.1)
        logger.info(
            f"Converting {amount_in_cents} cents into yearly credits. "
            "Formula: `amount_in_cents / cents_to_credit_ratio / 10 * 1.1`. "
            f"Cents to credit ratio: {cents_to_credit_ratio}. "
            f"Converted value: {value}."
        )
        return value
    elif credit_type == "one_time":
        no_of_credits = int(amount_in_cents / cents_to_credit_ratio)
        if added_manually:
            logger.info(
                f"Converting {amount_in_cents} cents into one-time credits "
                "added_manually. "
                "Formula: `amount_in_cents / cents_to_credit_ratio`. "
                f"Cents to credit ratio: {cents_to_credit_ratio}. "
                f"Converted value: {no_of_credits}."
            )
            return no_of_credits
        if 1000 > amount_in_cents >= 500:
            logger.info(
                f"Converting {amount_in_cents} cents into one-time credits. "
                "amount_in_cents is between 500 and 1000. "
                "Converted Credits value: 400. We do it like this because of VAT"
            )
            return 400
        elif 2000 > amount_in_cents >= 1000:
            logger.info(
                f"Converting {amount_in_cents} cents into one-time credits. "
                "amount_in_cents is between 1000 and 2000. "
                "Converted Credits value: 1000. We do it like this because of VAT"
            )
            return 1000
        elif 3000 > amount_in_cents >= 2000:
            logger.info(
                f"Converting {amount_in_cents} cents into one-time credits. "
                "amount_in_cents is between 2000 and 3000. "
                "Converted Credits value: 2200. We do it like this because of VAT"
            )
            return 2200
        else:
            logger.error(
                "We should not reach this point without falling into one of the "
                "above conditions. "
                f"Converting {amount_in_cents} cents into one-time credits."
                "Formula: `amount_in_cents / cents_to_credit_ratio`. "
                f"Cents to credit ratio: {cents_to_credit_ratio}. "
                f"Converted value: {no_of_credits}."
            )
            return no_of_credits


def format_text_json_to_pretty_print(text_json: str) -> str:
    try:
        parsed_json = json.loads(text_json)
        return json.dumps(parsed_json, indent=4, sort_keys=True)
    except json.JSONDecodeError:
        return text_json


def generate_random_string(length: int = 20) -> str:
    return "".join(
        random.choice(string.ascii_letters + string.ascii_uppercase)
        for _ in range(length)
    )


def get_client_ip(request):
    """Retrieve the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # If behind a proxy, X-Forwarded-For may contain multiple IPs
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_no_of_free_credits_at_account_creation() -> int:
    amount_in_cents = get_setting(
        key="credits_per_user_signup_in_cents",
        expected_type=int,
    )
    
    if amount_in_cents:
        no_of_free_credits = convert_cents_into_credit(
            amount_in_cents=amount_in_cents,
            credit_type="one_time",
            added_manually=True
        )
        
        return no_of_free_credits
    return 0