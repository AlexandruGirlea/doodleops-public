import time
import logging
from typing import Union

import redis.asyncio as redis
from fastapi import HTTPException, status

from core import settings
from schemas.redis_db import (
	REDIS_KEY_TTL_MAX,
	REDIS_KEY_API_COST,
	REDIS_KEY_LLM_COST,
	REDIS_KEY_USER_API_CALLS_LOG,
	REDIS_KEY_USER_API_DAILY_CALLS,
	REDIS_USER_API_CALL_LOCK,
	REDIS_KEY_USER_CREDIT_BOUGHT,
	REDIS_KEY_USER_API_DAILY_CALL_LIMIT,
	REDIS_KEY_METERED_SUBSCRIPTION_USERS,
	REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION,
	REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER,
	REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING,
	REDIS_KEY_WHATSAPP_MSG_PER_MINUTE_RATE,
	REDIS_KEY_WHATSAPP_MSG_PER_HOUR_RATE,
)
from common.other import generate_random_chars


logger = logging.getLogger(__name__)


async def get_redis_conn():
	redis_conn = redis.Redis(
		host=settings.REDIS_HOST,
		port=settings.REDIS_PORT,
		db=settings.REDIS_DB_DEFAULT,
	)
	try:
		yield redis_conn
	finally:
		await redis_conn.close()
		await redis_conn.connection_pool.disconnect()


async def get_redis_key_value(
		redis_conn: redis.Redis, key: str
) -> str:
	value = await redis_conn.get(key)
	if value:
		return value.decode()
	return ""


async def count_matching_keys(redis_conn: redis.Redis, key_pattern: str):
	total_keys = 0
	async for _ in redis_conn.scan_iter(match=key_pattern):
		total_keys += 1
	return total_keys


async def log_api_call(
	redis_conn: redis.Redis,
	timestamp: int,
	current_date: str,
	username: str,
	api_name: str,
	success: bool = False,
) -> None:
	await redis_conn.incr(
		name=REDIS_KEY_USER_API_DAILY_CALLS.format(
			username=username,
			date=current_date,
		),
		amount=1,
	)

	# we need to set the TTL again, because incr resets it
	await redis_conn.expire(
		name=REDIS_KEY_USER_API_DAILY_CALLS.format(
			date=current_date,
			username=username,
		),
		time=REDIS_KEY_TTL_MAX,
	)

	await redis_conn.set(
		name=REDIS_KEY_USER_API_CALLS_LOG.format(
			username=username,
			timestamp=str(timestamp),
			api_name=api_name,
		),
		value=int(success),
		ex=REDIS_KEY_TTL_MAX,
	)


async def sum_user_credits_bought(redis_conn: redis.Redis, username: str) -> int:
	total_credits_bought = 0
	truncated_key = (
		REDIS_KEY_USER_CREDIT_BOUGHT.rpartition(":")[0].format(username=username)
		+ ":*"
	)  # wildcard to match all keys

	async for key in redis_conn.scan_iter(match=truncated_key):
		purchase_value = await redis_conn.get(key)
		if purchase_value is not None:
			total_credits_bought += int(purchase_value)

	return total_credits_bought


async def decrement_user_bought_credits(
	redis_conn: redis.Redis,
	username: str,
	api_cost: int,
):
	"""
	This function will decrement the user's bought credits by the api_cost
	amount. If the user has enough credits, it will decrement the credits
	and return 0. If the user doesn't have enough credits, it will return
	the remaining number of credits that the user needs to pay.
	"""

	key_pattern = REDIS_KEY_USER_CREDIT_BOUGHT.format(
		username=username,
		id="*",
	)

	keys = [key async for key in redis_conn.scan_iter(match=key_pattern)]
	sorted_keys = sorted(
		# sort keys based on 'id'
		keys, key=lambda k: int(k.decode("utf-8").split(":")[-1])
	)

	for key in sorted_keys:
		current_key_value = int(await redis_conn.get(key))

		if current_key_value > api_cost:
			await redis_conn.decr(key, api_cost)
			return 0
		else:
			# if the current key value is less than the api_cost
			# decrement the api_cost and delete the key
			api_cost -= current_key_value
			await redis_conn.delete(key)

			if api_cost <= 0:
				return 0

	return api_cost


async def log_credits_used_per_api_endpoint_by_user(
	redis_conn: redis.Redis,
	username: str,
	api_name: str,
	api_cost: int,
	current_date: str,
	timestamp: int,
):
	key = REDIS_KEY_CREDITS_USED_PER_API_ENDPOINT_BY_USER.format(
		date=current_date,
		username=username,
		api_name=api_name,
		timestamp=timestamp,
		random_char=generate_random_chars(),
	)
	await redis_conn.set(
		name=key,
		value=api_cost,
		ex=REDIS_KEY_TTL_MAX,
	)


async def get_api_cost(
	redis_conn: redis.Redis, api_name: str
) -> Union[int, None]:
	api_cost = await redis_conn.get(REDIS_KEY_API_COST.format(api_name=api_name))

	if not api_cost:
		return None

	return int(api_cost.decode())


async def get_all_llm_costs(redis_conn: redis.Redis) -> dict:
	llm_costs_keys = [
		k.decode()
		for k in await redis_conn.keys(REDIS_KEY_LLM_COST.format(name="*"))
	]
	if not llm_costs_keys:
		return {}

	# for each key, get the value
	llm_costs = {}
	for key in llm_costs_keys:
		# make sure that the value is an integer
		value = int(await redis_conn.get(key))
		llm_costs[key.split(":")[-1]] = value
	return llm_costs


async def check_if_user_has_exceeded_daily_api_call_limit(
	redis_conn: redis.Redis,
	username: str,
	current_date: str,
) -> None:
	user_api_daily_call_limit = await redis_conn.get(
		name=REDIS_KEY_USER_API_DAILY_CALL_LIMIT.format(username=username)
	)

	if not user_api_daily_call_limit:
		logger.error(f"Daily API call limit not found for user {username}.")
		raise HTTPException(status_code=500, detail="Something went wrong.")

	user_api_daily_calls = await redis_conn.get(
		name=REDIS_KEY_USER_API_DAILY_CALLS.format(
			username=username,
			date=current_date,
		)
	)

	if user_api_daily_calls and (
		int(user_api_daily_calls.decode())
		>= int(user_api_daily_call_limit.decode())
	):
		logger.info(f"Daily API calls exceeded by user {username}.")
		raise HTTPException(status_code=401, detail="Daily API calls exceeded.")
	
	
async def get_user_subscriptions_monthly_credit_remaining(
	redis_conn: redis.Redis, username: str
) -> int:
	has_active_sub = await redis_conn.get(
		REDIS_KEY_USER_HAS_ACTIVE_SUBSCRIPTION.format(username=username)
	)
	
	has_active_sub = int(has_active_sub.decode()) if has_active_sub else 0
	if not has_active_sub:
		return 0
	
	subscriptions_monthly_credit_remaining = await redis_conn.get(
		REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
			username=username
		)
	)
	subscriptions_monthly_credit_remaining = (
		int(subscriptions_monthly_credit_remaining.decode())
		if subscriptions_monthly_credit_remaining
		else 0
	)
	return subscriptions_monthly_credit_remaining


async def check_if_user_has_enough_credits(
	redis_conn: redis.Redis, username: str, api_cost: int
):
	"""
	How it works, main steps:
	1. Check if the user has an active subscription
	2. If the user has an active subscription, check if the user has enough
		monthly credits remaining
	3. If the user doesn't have an active subscription, check if the user has
		enough bought credits
	4. If the user has enough credits, decrement the credits
	5. If the user doesn't have enough credits, raise an HTTPException
	"""
	credits_bought_remaining = await sum_user_credits_bought(
		redis_conn=redis_conn,
		username=username,
	)
	subscriptions_monthly_credit_remaining = (
		await get_user_subscriptions_monthly_credit_remaining(
			redis_conn=redis_conn,
			username=username,
		)
	)

	if api_cost > (
		subscriptions_monthly_credit_remaining + credits_bought_remaining
	):
		raise HTTPException(
			status_code=401, detail=settings.NOT_ENOUGH_CREDITS_MSG
		)


async def check_if_user_has_metered_subscription(
	redis_conn: redis.Redis, username: str
) -> bool:
	has_metered_subscription = await redis_conn.get(
		REDIS_KEY_METERED_SUBSCRIPTION_USERS.format(username=username)
	)
	if not has_metered_subscription:
		return False

	return True


async def update_user_credits(
	username: str,
	redis_conn: redis.Redis,
	api_cost: int,
) -> None:
	remaining_api_cost = await decrement_user_bought_credits(
		redis_conn=redis_conn,
		username=username,
		api_cost=api_cost,
	)

	if remaining_api_cost == 0:
		return

	# can do this because we already checked if the user has enough credits
	# with `check_if_user_has_enough_credits`
	await redis_conn.decr(
		name=REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING.format(
			username=username
		),
		amount=remaining_api_cost,
	)


async def set_user_api_call_lock(
	redis_conn: redis.Redis, username: str, api_name: str
) -> None:
	redis_user_lock_key = REDIS_USER_API_CALL_LOCK.format(
		username=username,
	)

	try:
		if await redis_conn.get(redis_user_lock_key):
			raise HTTPException(
				status_code=status.HTTP_429_TOO_MANY_REQUESTS,
				detail="Too many requests.",
			)

		await redis_conn.set(
			name=redis_user_lock_key,
			value=api_name,
			ex=30,
		)
	except HTTPException as e:
		raise e
	except Exception as e:
		logger.error(f"Error in set_user_api_call_lock: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Something went wrong.",
		)


async def release_user_api_call_lock(
	redis_conn: redis.Redis, username: str, api_name: str
) -> None:
	redis_user_lock_key = REDIS_USER_API_CALL_LOCK.format(
		username=username,
	)

	redis_api_name = await redis_conn.get(redis_user_lock_key)
	if redis_api_name and redis_api_name.decode() == api_name:
		await redis_conn.delete(redis_user_lock_key)


async def rate_limit_twilio_whatsapp_msg(
		sender_phone_number: str,  redis_conn: redis.Redis
):
	now = int(time.time())

	current_minute = now // 60
	current_hour = now // 3600

	minute_key = REDIS_KEY_WHATSAPP_MSG_PER_MINUTE_RATE.format(
		number=sender_phone_number, current_minute=current_minute
	)
	hour_key = REDIS_KEY_WHATSAPP_MSG_PER_HOUR_RATE.format(
		number=sender_phone_number, current_hour=current_hour
	)

	pipeline = await redis_conn.pipeline()
	pipeline.incr(minute_key)
	pipeline.expire(minute_key, 60)  # expires after 60s
	pipeline.incr(hour_key)
	pipeline.expire(hour_key, 3600)  # expires after 1h
	results = await pipeline.execute()

	if results and isinstance(results, list) and len(results) == 4:
		if (
				results[0] > settings.MAX_MSGS_PER_MINUTE or 
				results[2] > settings.MAX_MSGS_PER_HOUR
		):
			raise HTTPException(
				status_code=status.HTTP_429_TOO_MANY_REQUESTS,
				detail="Too many requests",
			)
		else:
			return
	else:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Something went wrong",
		)
