# for user authentication
REDIS_KEY_USER_GENERATED_TOKEN = "token:user_generated:{token}:username"
REDIS_OPENAI_OAUTH_USER_GENERATED_TOKEN = "token:openai_oauth:{token}:username"

# for metering api calls
REDIS_KEY_LLM_COST = "llm_cost:{name}"
REDIS_KEY_API_COST = "api_cost:{api_name}"
REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION = "user_has_active_subscription:{username}"

REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING = (
    "subscriptions_monthly_credit_remaining:{username}"
)
REDIS_KEY_USER_API_DAILY_CALL_LIMIT = "user_api_daily_call_limit:{username}"
REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER = (
    "credits_used_per_api_endpoint_by_user:{date}:{username}:{api_name}:"
    "{timestamp}:{random_char}"
)
# the {id} of the `CustomerCreditsBought` model
REDIS_KEY_USER_CREDIT_BOUGHT = "user_credit_bought:{username}:{id}"

# for stripe login
# no need to delete this because the customer's email will e anonimized on Stripe
REDIS_KEY_STRIPE_CUSTOMER_ID_EVENTS = (
    "stripe:{customer_id}:{event_type}:{event_id}"
)

# we will store a timestamp of when the user last made a call
REDIS_KEY_USER_DJANGO_CALL_RATE_LIMIT = "user_django_call_rate_limit:{username}"
REDIS_KEY_METERED_SUBSCRIPTION_USERS = "metered_subscription_users:{username}"

# {
#   "user_phone_number:{number}":
#   '{"email": "test@doodleops.com", "phone_number": "12390", "username": "test"}'
#  }
REDIS_KEY_USER_PHONE_NUMBER = "user_phone_number:{number}"

ENTERPRISE_USER_MAX_CREDITS_LIMIT_PER_MONTH = (
    "enterprise_user_max_credits_limit_per_month:{username}"
)
