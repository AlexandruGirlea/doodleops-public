import json
import logging
from datetime import datetime

from fastapi.responses import Response
from fastapi import status, Request, Depends

from core.urls import urls
from core.settings import GENERIC_ERROR_MSG
from schemas.urls import CloudRunAPIEndpoint
from access_management.api_auth import verify_twilio_whatsapp
from common.external_resources import publish_whatsapp_msg_to_pubsub
from common.redis_utils import (
	get_redis_key_value, get_redis_conn, rate_limit_twilio_whatsapp_msg,
	check_if_user_has_metered_subscription, get_all_llm_costs, log_api_call,
	check_if_user_has_exceeded_daily_api_call_limit, sum_user_credits_bought,
	get_user_subscriptions_monthly_credit_remaining
)
from app_ai.cloud_run_container_app_ai.v1.common.pub_sub_schema import (
	TwilioPublisherMsg, LLMCost
)
from app_ai.views.v1.fastapi_views.route import v1_view_ai_router
from app_ai.cloud_run_container_app_ai.v1.common.redis_schemas import (
	REDIS_KEY_USER_PHONE_NUMBER
)

APP_NAME, VERSION, API = ("app_ai", "v1", "twilio_whatsapp_webhook")
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]

logger = logging.getLogger("APP_API_"+API_NAME+__name__)
logger.propagate = True


@v1_view_ai_router.post(URL_DATA.api_url, include_in_schema=True)
async def v1_twilio_whatsapp_webhook(
		request: Request,
		sender_phone_number=Depends(verify_twilio_whatsapp),
		redis_conn=Depends(get_redis_conn),
) -> Response:
	# raises HTTPException if rate limit exceeded per min or hour
	await rate_limit_twilio_whatsapp_msg(
		sender_phone_number=sender_phone_number, redis_conn=redis_conn
	)
	body = await request.form()  # FormData object
	post_params = dict(body)
	logger.info(f"post_params: {post_params}")

	user_data = await get_redis_key_value(
		redis_conn=redis_conn,
		key=REDIS_KEY_USER_PHONE_NUMBER.format(number=sender_phone_number)
	)

	username = json.loads(user_data).get("username") if user_data else None

	current_date = datetime.now().strftime("%d-%m-%Y")
	timestamp = int(datetime.now().timestamp())
	
	if username:
		await log_api_call(
			redis_conn=redis_conn,
			current_date=current_date,
			username=username,
			api_name="whatsapp_ai",
			timestamp=timestamp,
			success=True,
		)
	
	twilio_publisher_msg = TwilioPublisherMsg(
			phone_number=sender_phone_number,
			username=username,
			msg=post_params.get("Body", ""),
			media_url=post_params.get("MediaUrl0", ""),
			media_type=post_params.get("MediaContentType0", ""),
			timestamp=timestamp,
	)
	if username:
		twilio_publisher_msg.has_metered_subscription = (
			await check_if_user_has_metered_subscription(
				redis_conn=redis_conn,
				username=username,
			)
		)
		twilio_publisher_msg.user_credits_bought_remaining = (
			await sum_user_credits_bought(
				redis_conn=redis_conn,
				username=username,
			)
		)
		twilio_publisher_msg.subscriptions_monthly_credit_remaining = (
			await get_user_subscriptions_monthly_credit_remaining(
				redis_conn=redis_conn,
				username=username,
			)
		)
		all_llm_costs = await get_all_llm_costs(redis_conn)
		twilio_publisher_msg.all_llm_costs = LLMCost(**all_llm_costs)

	resp = publish_whatsapp_msg_to_pubsub(input_data=twilio_publisher_msg)

	if resp:
		return Response(status_code=status.HTTP_204_NO_CONTENT)
	
	return Response(
		content=GENERIC_ERROR_MSG,
		media_type="text/xml",
		status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
	)
