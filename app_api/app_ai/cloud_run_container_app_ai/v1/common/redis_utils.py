import json
import string
import random
import logging
from typing import Union
from datetime import datetime, timedelta

import redis

from core import settings
from common.redis_schemas import (
	REDIS_KEY_USER_WHATSAPP_MSG, REDIS_KEY_UNKNOWN_USER_WHATSAPP_TIMESTAMP,
	REDIS_KEY_USER_PHONE_NUMBER, REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER,
	REDIS_KEY_USER_CREDIT_BOUGHT, REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
	ENTERPRISE_USER_MAX_CREDITS_LIMIT_PER_MONTH
)
from common.pub_sub_schema import LLMCost
from common.twilio_utils import send_whatsapp_message


logger = logging.getLogger("APP_AI_V1_"+__name__)


class RedisClient:
	def __init__(self):
		self._instance = None

	def __enter__(self):
		if self._instance is None:
			self._instance = redis.Redis(
				host=settings.REDIS_HOST,
				port=settings.REDIS_PORT,
				db=settings.REDIS_DB_DEFAULT,
			)
		return self._instance

	def __exit__(self, exc_type, exc_value, traceback):
		if self._instance is not None:
			self._instance.connection_pool.disconnect()
			self._instance = None

	def type(self, key):
		if self._instance is not None:
			return self._instance.type(key)
		return None
		

def get_redis_key(
	key: str,
	min_timestamp: Union[int, float, str] = "-inf",
	max_timestamp: Union[int, float, str] = "+inf",
) -> Union[str, list] or None:
	"""
	Get redis key value or sorted set based on different parameters
		:param key: the redis key
		:param min_timestamp: minimum score for ZRANGEBYSCORE
		:param max_timestamp: maximum score for ZRANGEBYSCORE
		:return: value or list of values
	"""
	try:
		with RedisClient() as client:
			redis_key_type = client.type(key).decode("utf-8")

			if redis_key_type == "none":
				logger.warning(f"The key {key} does not exist.")
				return None

			elif (
				redis_key_type == "string"
				and min_timestamp == "-inf"
				and max_timestamp == "+inf"
			):
				return client.get(key).decode("utf-8")

			elif redis_key_type == "zset":
				return [
					json.loads(x.decode("utf-8"))
					for x in client.zrangebyscore(
						key, min_timestamp, max_timestamp
					)
				]
			logger.error(
				f"The key {key} holds a type {redis_key_type}, can't be handled."
			)

	except Exception as e:
		logger.error(e)
	
	return None


def set_redis_key(
	key: str,
	simple_value: Union[str, int, float] = None,
	expire: int = None,
	timed_value: dict = None,
	timestamp: Union[int, float] = None,
) -> bool:
	"""
	Set redis key
		:param key: name
		:param simple_value: simple value
		:param expire: number of seconds until the key expires. Not a timestamp!
		:param timed_value: dictionary that will be stored as a JSON string
		:param timestamp: is used as the score for the timed value to sort by
		:return: True if success or Raise ValueError
	"""
	with RedisClient() as client:
		if simple_value or simple_value == 0:
			if expire:
				client.setex(key, expire, simple_value)
			else:
				client.set(key, simple_value)

		elif timed_value and timestamp:
			timed_value_str = json.dumps(timed_value)
			client.zadd(key, {timed_value_str: timestamp})

			# If expire is provided, set an expiration for the sorted set.
			if expire:
				client.expire(key, expire)
		else:
			raise ValueError(
				"Either value or both timed_value and timestamp must be provided."
			)
	return True


def get_user_msgs_from_db(username: str):
	user_db_msgs = get_redis_key(
		key=REDIS_KEY_USER_WHATSAPP_MSG.format(username=username)
	)
	return json.loads(user_db_msgs) if user_db_msgs else {"msgs": []}


def update_user_msgs(
		username: str, timestamp: int, assistant_msg: str = "",
		user_msg: str = "", user_is_first: bool = False,
) -> dict:
	"""
	Very important to be aware of the order of the messages. This variable
	`user_is_first` is used to determine if the user message should be added
	first or last in the list of messages.

	Also at least one of the two messages must be provided or both.
	"""
	if not username or not any([assistant_msg, user_msg]):
		logger.error(
			"Username and at least one of the two messages must be provided."
		)
		return {"msgs": []}

	user_db_msgs = get_user_msgs_from_db(username)

	msgs_to_append = []

	if user_msg:
		user_msg = {
					"role": "user", "content": user_msg,
					"timestamp": timestamp
				}
	if assistant_msg:
		assistant_msg = {
					"role": "assistant", "content": assistant_msg,
					"timestamp": timestamp
				}

	if user_is_first:
		if user_msg:
			msgs_to_append.append(user_msg)
		if assistant_msg:
			msgs_to_append.append(assistant_msg)
	else:  # assistant is first
		if assistant_msg:
			msgs_to_append.append(assistant_msg)
		if user_msg:
			msgs_to_append.append(user_msg)

	user_db_msgs["msgs"].extend(msgs_to_append)

	if len(user_db_msgs["msgs"]) > settings.MAX_NUMBER_OF_HISTORY_MSGS:
		user_db_msgs["msgs"] = (
			user_db_msgs["msgs"][-settings.MAX_NUMBER_OF_HISTORY_MSGS:]
		)
	set_redis_key(
		key=REDIS_KEY_USER_WHATSAPP_MSG.format(username=username),
		simple_value=json.dumps(user_db_msgs),
		expire=60 * 60 * 24 * 30 * 3  # in 3 months
	)
	return user_db_msgs


def get_localized_error_message(phone_number):
	"""
	Returns a localized error message based on the country code found in the phone
	number.
	If no matching country code is found, it defaults to English.
	"""
	for code, lang in settings.COUNTRY_PHONE_CODES_AND_LANGUAGES.items():
		if phone_number.startswith(code):
			return settings.GENERIC_NO_ACCOUNT_ERROR_MSG.get(
				lang, settings.GENERIC_NO_ACCOUNT_ERROR_MSG["en"]
			)
	return settings.GENERIC_NO_ACCOUNT_ERROR_MSG["en"]


def check_if_msg_is_a_duplicate(timestamp: int, user_db_msgs: dict) -> bool:
	"""
	Check if the msg is a duplicate (we might get them from Pub/Sub & EventArc)
	we should not need to worry about multiple msgs because there is a rate
	limit at app_api level
	"""
	for m in user_db_msgs["msgs"]:
		if m["role"] == "user" and m["timestamp"] == timestamp:
			return True

	return False


def unknown_user_rate_limit(phone_number: str, timestamp: int):
	if not phone_number:
		return
	
	timestamp_key_value = get_redis_key(
		key=REDIS_KEY_UNKNOWN_USER_WHATSAPP_TIMESTAMP.format(
			phone_number=phone_number
		)
	)
	
	# duplicate Pub/Sub message
	if timestamp_key_value and int(timestamp_key_value) == timestamp:
		return
	
	if not timestamp_key_value:
		set_redis_key(
			key=REDIS_KEY_UNKNOWN_USER_WHATSAPP_TIMESTAMP.format(
				phone_number=phone_number
			),
			simple_value=timestamp,
			expire=60*30  # 30 minutes
		)
		send_whatsapp_message(
			to_phone_number=phone_number,
			body=get_localized_error_message(phone_number)
		)


def check_phone_numer_belongs_to_user(
		twilio_phone_number: str, twilio_username: str
) -> bool:
	redis_user_info = get_redis_key(
		key=REDIS_KEY_USER_PHONE_NUMBER.format(number=twilio_phone_number)
	)

	try:
		redis_user_info = json.loads(redis_user_info)
		username = redis_user_info.get("username")
	except Exception as e:
		logger.error(f"Error: {e}")
		return False

	if username != twilio_username:
		logger.error(
			f"Phone number {twilio_phone_number} is not associated with "
			f"username {twilio_username}"
		)
		send_whatsapp_message(
			to_phone_number=twilio_phone_number,
			body=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT
		)
		return False
	return True


# COST LOGIC
def decrement_user_bought_credits(username: str, call_cost: int) -> int:
	"""
	This function will decrement the user's bought credits by the call_cost
	amount. If the user has enough credits, it will decrement the credits
	and return 0. If the user doesn't have enough credits, it will return
	the remaining number of credits that the user needs to pay.
	"""
	key_pattern = REDIS_KEY_USER_CREDIT_BOUGHT.format(username=username, id="*")
	with RedisClient() as redis_conn:
		keys = [key for key in redis_conn.scan_iter(match=key_pattern)]
		sorted_keys = sorted(
			# sort keys based on 'id'
			keys, key=lambda k: int(k.decode("utf-8").split(":")[-1])
		)

		for key in sorted_keys:
			current_key_value = int(redis_conn.get(key))
	
			if current_key_value > call_cost:
				redis_conn.decr(key, call_cost)
				return 0
			else:
				# if the current key value is less than the call_cost
				# decrement the call_cost and delete the key
				call_cost -= current_key_value
				redis_conn.delete(key)
	
				if call_cost <= 0:
					return 0
	
		return call_cost


def update_user_credits(username: str, call_cost: int) -> None:
	remaining_call_cost = decrement_user_bought_credits(
		username=username, call_cost=call_cost,
	)

	if remaining_call_cost == 0:
		return
	
	subs_remaining_key = REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
		username=username
	)
	with RedisClient() as redis_conn:
		subs_remaining_value = redis_conn.get(subs_remaining_key)
		
		if subs_remaining_value:
			value = int(subs_remaining_value)
			if value >= remaining_call_cost:
				redis_conn.decr(
					name=subs_remaining_key, amount=remaining_call_cost)
			else:
				redis_conn.set(name=subs_remaining_key, value=0)
			


def log_credits_used_per_api_endpoint_by_user(
	username: str, api_name: str, call_cost: int, current_date: str,
	timestamp: int,
):
	characters = string.ascii_letters + string.digits
	with RedisClient() as redis_conn:
		key = REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.format(
			date=current_date,
			username=username,
			api_name=api_name,
			timestamp=timestamp,
			random_char="".join(random.choice(characters) for _ in range(5))
		)
		redis_conn.set(
			name=key,
			value=call_cost,
			ex=settings.REDIS_KEY_TTL_MAX,
		)


def get_credits_used_by_user_x_days_ago(days: int, username: str) -> int:
	"""
	Get the credits used by the user X days ago
	"""
	
	total_credits_used = 0
	with RedisClient() as client:
		for i in range(days):
			current_date = (
					datetime.now() - timedelta(days=i)).strftime("%d-%m-%Y")
			
			key_pattern = (
				f"credits_used_per_api_endpoint_by_user:{current_date}:"
				f"{username}:*"
			)
			
			total_for_day = 0
			cursor = 0
			
			while True:
				cursor, keys = client.scan(cursor, match=key_pattern, count=1000)
				if keys:
					pipeline = client.pipeline()
					for key in keys:
						pipeline.get(key)
					results = pipeline.execute()

					total_for_day += sum(
						int(val) for val in results if val is not None)
				if cursor == 0:
					break
			
			total_credits_used += total_for_day
				
	return total_credits_used


def get_total_call_cost(default_costs: LLMCost, all_llm_costs: LLMCost) -> int:
	"""
	Process the cost of the LLM call
	"""
	if not all_llm_costs.simple_conversation:
		all_llm_costs.simple_conversation = default_costs.simple_conversation
	
	return sum(all_llm_costs.model_dump().values())


def consume_user_credits(
		username: str, call_cost: int, current_date: str, timestamp: int,
		api_name: str, has_metered_subscription: bool = False,
) -> None:
	if not has_metered_subscription:
		update_user_credits(username=username, call_cost=call_cost)
	
	log_credits_used_per_api_endpoint_by_user(
		username=username,
		api_name=api_name,
		call_cost=call_cost,
		current_date=current_date,
		timestamp=timestamp,
	)


def get_max_credits_per_month_for_enterprise_user(username: str) -> int:
	"""
	Get the max credits per month for an enterprise user
	"""
	max_credits = get_redis_key(
		key=ENTERPRISE_USER_MAX_CREDITS_LIMIT_PER_MONTH.format(username=username)
	)
	return int(max_credits) if max_credits else 5000


def does_user_have_enough_credits(
		username: str, api_cost: int, user_total_available_credits: int,
		has_metered_subscription: bool = False,
) -> bool:
	if has_metered_subscription:
		credits_already_used = get_credits_used_by_user_x_days_ago(
			days=30, username=username
		)
		logger.info(f"credits_already_used: {credits_already_used}")
		max_credits_allowed_per_month = get_max_credits_per_month_for_enterprise_user(
			username=username
		)
		logger.info(f"max_credits_allowed_per_month: {max_credits_allowed_per_month}")
		if credits_already_used + api_cost > max_credits_allowed_per_month:
			return False
		return True
	
	return user_total_available_credits >= api_cost
