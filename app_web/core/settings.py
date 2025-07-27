import os
import json
import logging
from pathlib import Path

import stripe
import firebase_admin as fb_admin
from celery.schedules import crontab

from common.os_env_var_management import get_env_variable
from common.secrets_manager import set_app_web_secrets

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_MODE = get_env_variable("ENV_MODE", "").lower()

if ENV_MODE != "local":
    set_app_web_secrets()

SECRET_KEY = get_env_variable("SECRET_KEY")

DEBUG = get_env_variable("DEBUG", "").lower() == "true" or False

CSRF_TRUSTED_ORIGINS = [
    "https://dev.doodleops.com", "http://dev.doodleops.com"
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = get_env_variable("ALLOWED_HOSTS").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "oauth2_provider",
    "app_api",
    "app_contact",
    "app_pages",
    "app_financial",
    "app_users",
    "app_settings",
]

MIDDLEWARE = [
    "core.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.Handle404Middleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": get_env_variable("MYSQL_DATABASE", ""),
        "USER": get_env_variable("MYSQL_USER", ""),
        "PASSWORD":get_env_variable("MYSQL_PASSWORD", ""),
        "HOST": get_env_variable("MYSQL_HOST", ""),
        "PORT": get_env_variable("MYSQL_PORT", ""),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {"auth_plugin": "mysql_native_password"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation."
        "NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

if ENV_MODE == "local":
    # Serve static files locally for development
    STATIC_URL = "/static/"
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, "static"),
    ]
    # Uncomment the following line if you want to collect static files
    # STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
elif "dev" in ENV_MODE:
    STATIC_URL = "https://dev-static.doodleops.com/"
else:  # this is prod
    STATIC_URL = "https://static.doodleops.com/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "app_users.CustomUser"
DEFAULT_USER_API_DAILY_CALL_LIMIT = 200


# ------------ Firebase and oAuth2
TOKEN_COOKIE_NAME = "doodlepops-api-token"

FIREBASE_KEY_JSON = json.loads(
    get_env_variable("FIREBASE_KEY_JSON").replace("'", '"'))

if FIREBASE_KEY_JSON:
    fb_admin.initialize_app(fb_admin.credentials.Certificate(FIREBASE_KEY_JSON))

FIREBASE_CONFIG = json.loads(
    get_env_variable("FIREBASE_CONFIG_JSON").replace("'", '"'))

FIREBASE_CONFIG = FIREBASE_CONFIG if FIREBASE_CONFIG else {"apiKey": ""}

GCP_JWT_AUTH_URL = (
    "https://www.googleapis.com/identitytoolkit/v3/relyingparty/"
    f"verifyPassword?key={FIREBASE_CONFIG['apiKey']}"
)

FB_ACCOUNT_LINKING_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:"
)
FB_SIGNIN_WITH_IDP_URL = (  # SSO with Google
        "".join([
            FB_ACCOUNT_LINKING_URL, "signInWithIdp?key=",
            FIREBASE_CONFIG["apiKey"]
        ])
    )
FB_SEND_OOBCODE_URL = (  # Send verification email & password reset
        "".join([
            FB_ACCOUNT_LINKING_URL, "sendOobCode?key=",
            FIREBASE_CONFIG["apiKey"]
        ])
    )

FB_ACCOUNT_DELETE_URL = (  # Delete user
        "".join([
            FB_ACCOUNT_LINKING_URL, "delete?key=",
            FIREBASE_CONFIG["apiKey"]
        ])
    )

OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 86400,
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 300,
    'APPLICATION_MODEL': 'oauth2_provider.Application',
    'REFRESH_TOKEN_EXPIRE_SECONDS': 864000,
    'PKCE_REQUIRED': False,
}

# ------------ end of Firebase


# ------------ FastAPI
FASTAPI_HOST = get_env_variable("FASTAPI_HOST")
CRYPT_SECRET_KEY_WEB = get_env_variable("CRYPT_SECRET_KEY_WEB")
# ------------ end of FastAPI


# ------------ Stripe
stripe.api_key = get_env_variable("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = get_env_variable("STRIPE_WEBHOOK_SECRET")
STRIPE_PUBLISHABLE_KEY = get_env_variable("STRIPE_PUBLISHABLE_KEY")
# ------------ end of Stripe


# ------------ Redis
REDIS_HOST = get_env_variable("REDIS_HOST")
REDIS_PORT = get_env_variable("REDIS_PORT")
REDIS_DB_DEFAULT = get_env_variable("REDIS_DB_DEFAULT")
# ------------ end of Redis


# ------------ Google SSO
GOOGLE_PROJECT_ID = get_env_variable("GOOGLE_PROJECT_ID")
GOOGLE_SERVICE_ACCOUNT_KEY_JSON =  json.loads(
        get_env_variable("GOOGLE_SERVICE_ACCOUNT_KEY_JSON").replace("'", '"'))

if GOOGLE_SERVICE_ACCOUNT_KEY_JSON:
    GOOGLE_SERVICE_ACCOUNT_KEY_JSON["private_key"] = (
        GOOGLE_SERVICE_ACCOUNT_KEY_JSON["private_key"].replace("\\n", "\n")
    )
GOOGLE_CLIENT_ID = get_env_variable("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = get_env_variable("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = get_env_variable("GOOGLE_REDIRECT_URI")
# ------------ end of Google SSO


# ------------ Slack
SLACK_WEBHOOK_URL = get_env_variable("SLACK_WEBHOOK_URL")
# ------------ end of Slack


# ------------ Recaptcha
RECAPTCHA_PUBLIC_KEY = get_env_variable("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_REQUIRED_SCORE = 0.6
# ------------ end of Recaptcha

# ------------ Email
EMAIL_DOMAIN_PATH = get_env_variable("EMAIL_DOMAIN_PATH")
EMAIL_DOMAIN_PATH = (
    EMAIL_DOMAIN_PATH
    if not EMAIL_DOMAIN_PATH.endswith("/") else
    EMAIL_DOMAIN_PATH[:-1]
)
AWS_SES_DOMAIN = get_env_variable("AWS_SES_DOMAIN")
AWS_SES_ACCESS_KEY = get_env_variable("AWS_SES_ACCESS_KEY")
AWS_SES_SECRET_KEY = get_env_variable("AWS_SES_SECRET_KEY")
AWS_SES_REGION = get_env_variable("AWS_SES_REGION")

DEFAULT_SUPPORT_EMAIL = "support@doodleops.com"
# ------------ end of Email

# ------------ Zendesk
ZENDESK_API_TOKEN = os.getenv('ZENDESK_API_TOKEN')
ZENDESK_SUBDOMAIN = os.getenv('ZENDESK_SUBDOMAIN')
ZENDESK_USER_EMAIL = os.getenv('ZENDESK_USER_EMAIL')
if not all([ZENDESK_API_TOKEN, ZENDESK_SUBDOMAIN, ZENDESK_USER_EMAIL]):
    logger.error("One or more Zendesk environment variables are not set.")
    raise EnvironmentError("Missing Zendesk configuration.")
# ------------ end of Zendesk

# ------------ Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
# ------------ end of Twilio

# ------------ Celery
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_DEFAULT}"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_DEFAULT}"

CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_BEAT_SCHEDULE = {
    "cronjob_store_api_counter_obj_for_the_previous_day": {
        "task": (
            "app_api.tasks.cronjob_store_api_counter_obj_for_the_previous_day"
        ),
        "schedule": crontab(hour="0,3,6,9,12,15,18,21", minute="10"),
    },
    "cronjob_send_subscription_item_metered_usage_to_stripe": {
        "task": (
            "app_financial.tasks."
            "cronjob_send_subscription_item_metered_usage_to_stripe"
        ),
        "schedule": crontab(hour="0,3,6,9,12,15,18,21", minute="30"),
    },
    # run every day at midnight + 2 minutes
    "remove_expired_credits": {
        "task": "app_financial.tasks.remove_expired_credits",
        "schedule": crontab(hour="0", minute="2"),
    },
    "has_api_counter_discrepancies": {
        "task": "app_api.tasks.has_api_counter_discrepancies",
        "schedule": crontab(hour="2", minute="5"),
    },
    "task_charge_deleted_metered_subscription_draft_invoices": {
        "task": (
            "app_financial.tasks."
            "task_charge_deleted_metered_subscription_draft_invoices"
        ),
        # run every hour + 6 minutes
        "schedule": crontab(minute="6"),
    },
    "clear_oauth2_tokens": {
        "task": "app_users.tasks.clear_oauth2_tokens",
        "schedule": crontab(hour="0,3,6,9,12,15,18,21", minute="30"),
    },
    "task_add_monthly_credits_to_yearly_subscriptions": {
        "task": (
            "app_financial.tasks."
            "task_add_monthly_credits_to_yearly_subscriptions"
        ),
        "schedule": crontab(minute="*/30"),
    }
}

# ------------ Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": (
                "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s"
            ),
            "datefmt": "%d-%m-%Y %H:%M:%S",
        },
    },
    "handlers": {
        # Console handler (writes to stdout)
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO" if DEBUG else "INFO",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "INFO",
            "propagate": True,
        },
    },
}
# ------------ end of Logging
