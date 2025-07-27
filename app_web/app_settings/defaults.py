"""
Example of default settings for the app.

DEFAULT_SETTINGS = {
    'credits_per_user_signup_in_cents': {
        'value': 20,
        'type': int,
        'description': "The amount of credits to give to a user when they sign up.",
    },
    'welcome_message': {
        'value': 'Welcome to our platform!',
        'type': str,
        'description': "The welcome message displayed to new users.",
    },
    'feature_enabled': {
        'value': True,
        'type': bool,
        'description': "Flag to enable or disable a feature.",
    },
    'launch_date': {
        'value': datetime.datetime(2023, 12, 31),
        'type': datetime.datetime,
        'description': "The scheduled launch date of the new feature.",
    },
    'extra_settings': {
        'value': {'option1': True, 'option2': False},
        'type': dict,
        'description': "Extra configuration settings in JSON format.",
    },
}
"""
from django.conf import settings

DEFAULT_SETTINGS = {
    'credits_per_user_signup_in_cents': {
        'value': 200,
        'type': int,
        'description': (
            "The amount of credits to give to a user when they sign up.",
        ),
    },
    'max_accounts_per_user_in_time_window': {
        'value': 10 if settings.ENV_MODE == 'local' else 2,
        'type': int,
        'description': "The maximum number of accounts a user can create.",
    },
    'time_window_max_accounts_per_user_in_hours': {
        'value': 24,
        'type': int,
        'description': "The maximum number of accounts a user can create.",
    },
    "cents_to_credit_ratio": {
            "value": 1.0,
            "type": float,
            "description": "The ratio of cents to credits. 1 cent = 1 credit.",
        },
    "calendly_url": {
        "value": "https://calendly.com/something/15min",
        "type": str,
        "description": "The URL to your Calendly page.",
    },
    "email_base_html_logo_path": {
        "value": "/app_web/static/logo.png",
        "type": str,
        "description": "The path to the logo image for the email template.",
    },
    "email_contact_response_time": {
        "value": "1-2",
        "type": str,
        "description": "Ex: `1-2` this is in business days.",
    },
    "zendesk_ticket_groups": {
        "value": '{"Billing": 29255862532753, "Feature Suggestion": 30478545173777, "Feedback": 29258048961809, "Sales": 29255902490001, "Support": 29203569010961}',
        "type": str,
        "description": (
            "Ex: `This is generated using "
            "common.zendesk.get_zendesk_ticket_groups()`"
        ),
    },
    "maintenance_email_message": {
        "value": "We are performing maintenance on our servers.....",
        "type": str,
        "description": "The message to include in the maintenance email.",
    },
    "default_user_api_daily_call_limit": {
        "value": 1000,
        "type": int,
        "description": "The daily API call limit for a user.",
    },
    "enterprise_api_daily_call_limit": {
        "value": 10000,
        "type": int,
        "description": "The daily API call limit for a enterprise.",
    },
    "credits_expire_days": {
        "value": 90,
        "type": int,
        "description": "The number of days before credits expire.",
    },
    "phone_number_list_of_allowed_countries": {
        "value": "US,CA,GB,FR,DE,ES,IT,PT,JP,IN,GR",
        "type": str,
        "description": "A comma separated list of allowed countries.",
    },
    "phone_number_list_of_allowed_country_codes": {
        "value": "+1,+44,+33,+49,+34,+39,+81,+91,+30,+351",
        "type": str,
        "description": "A comma separated list of allowed countries.",
    },
}
