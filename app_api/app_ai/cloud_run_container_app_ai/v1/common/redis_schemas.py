"""
# only keep the last 10 msgs => REDIS_KEY_USER_WHATSAPP_MSG max length 10
REDIS_KEY_USER_WHATSAPP_MSG = {
	"msgs": [
	{"role": "user", "content": "Hi!", "timestamp": 1630000000},
	{"role": "assistant", "content": "Hi, how can I help you?", timestamp": 1630000001},
	]
"""
REDIS_KEY_USER_WHATSAPP_MSG = "user_whatsapp_msg:{username}"


"""unknown_user_whatsapp_timestamp:{phone_number} -> 1630000000"""
REDIS_KEY_UNKNOWN_USER_WHATSAPP_TIMESTAMP = (
	"unknown_user_whatsapp_timestamp:{phone_number}"
)

"""
{
	"user_phone_number:{number}":
	'{"email": "test@doodleops.com", "username": "test"}'
}
"""
REDIS_KEY_USER_PHONE_NUMBER = "user_phone_number:{number}"

# Common Keys with App_API
REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER = (
	"credits_used_per_api_endpoint_by_user:{date}:{username}:{api_name}:"
	"{timestamp}:{random_char}"
)
REDIS_KEY_USER_CREDIT_BOUGHT = "user_credit_bought:{username}:{id}"
REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING = (
	"subscriptions_monthly_credit_remaining:{username}"
)
ENTERPRISE_USER_MAX_CREDITS_LIMIT_PER_MONTH = (
	"enterprise_user_max_credits_limit_per_month:{username}"
)
