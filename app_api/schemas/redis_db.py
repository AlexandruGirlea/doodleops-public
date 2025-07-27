from app_ai.cloud_run_container_app_ai.v1.common.redis_schemas import (
    REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
    REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER,
    REDIS_KEY_USER_CREDIT_BOUGHT
)

REDIS_KEY_TTL_MAX = 60 * 60 * 24 * 31 * 6  # 6 months

# for user authentication
REDIS_KEY_USER_GENERATED_TOKEN = "token:user_generated:{token}:username"
REDIS_OPENAI_OAUTH_USER_GENERATED_TOKEN = "token:openai_oauth:{token}:username"

# for metering api calls
REDIS_KEY_API_COST = "api_cost:{api_name}"

REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION = "user_has_active_subscription:{username}"

REDIS_KEY_USER_API_DAILY_CALL_LIMIT = "user_api_daily_call_limit:{username}"

# we store the Number of calls made per day per user
REDIS_KEY_USER_API_DAILY_CALLS = "user_api_daily_calls:{username}:{date}"
# we store which API endpoint was called and if it was a success or not (0/1)
REDIS_KEY_USER_API_CALLS_LOG = (
    "user_api_calls_log:{username}:{api_name}:{" "timestamp}"
)
# we lock the user from making more than one api call at a time
REDIS_USER_API_CALL_LOCK = "user_is_making_api_call:{username}"

# we only store value 1 for the key
REDIS_KEY_METERED_SUBSCRIPTION_USERS = "metered_subscription_users:{username}"

# This is for the WhatsApp API rate limiting
REDIS_KEY_WHATSAPP_MSG_PER_MINUTE_RATE = (
    "whatsapp_msg_per_minute_rate:{number}:{current_minute}"
)
REDIS_KEY_WHATSAPP_MSG_PER_HOUR_RATE = (
    "whatsapp_msg_per_hour_rate:{number}:{current_hour}"
)
REDIS_KEY_LLM_COST = "llm_cost:{name}"
