"""
This will become the router for all LLM Actions
"""

import json
import time
import base64
import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from core import settings
from views.urls import urls
from access_management.api_auth import verify_auth
from common.redis_utils import (
	update_user_msgs, get_user_msgs_from_db,
	check_if_msg_is_a_duplicate, unknown_user_rate_limit,
	check_phone_numer_belongs_to_user, consume_user_credits
)
from llm_graph.main_supervisor import call_main_supervisor
from llm_graph.utils.file_management import process_media_url
from common.pub_sub_schema import TwilioPublisherMsg, LLMCost
from common.twilio_utils import send_whatsapp_message, split_on_symbols

logger = logging.getLogger("APP_AI_V1_"+__name__)

ai_twilio_router = APIRouter(
	tags=["Twilio"],
	responses={404: {"description": "Not found"}},
)

API_NAME = "app_ai/v1/view_ai_whatsapp"  # neede for cost management


@ai_twilio_router.post(urls.get("view_ai_twilio"), include_in_schema=True)
async def view_ai_twilio(
		request: Request, auth: bool = Depends(verify_auth)
) -> JSONResponse:
	req_json = await request.json()
	twilio_dict = json.loads(base64.b64decode(req_json["message"]["data"]))
	twilio_dict["all_llm_costs"] = LLMCost(**twilio_dict["all_llm_costs"])
	twilio_obj = TwilioPublisherMsg(**twilio_dict)

	if not twilio_obj.username:
		return unknown_user_rate_limit(
			phone_number=twilio_obj.phone_number,
			timestamp=twilio_obj.timestamp,
		)

	if not check_phone_numer_belongs_to_user(
			twilio_phone_number=twilio_obj.phone_number,
			twilio_username=twilio_obj.username
	):
		return JSONResponse(status_code=200, content={"message": "Success"})
	
	if not twilio_obj.msg and not twilio_obj.media_url:
		return JSONResponse(status_code=200, content={"message": "Success"})
	
	user_db_msgs = get_user_msgs_from_db(username=twilio_obj.username)

	if check_if_msg_is_a_duplicate(
			timestamp=twilio_obj.timestamp, user_db_msgs=user_db_msgs
	):
		return JSONResponse(status_code=200, content={"message": "Success"})
	
	user_total_available_credits = (
			twilio_obj.user_credits_bought_remaining +
			twilio_obj.subscriptions_monthly_credit_remaining
	)

	min_cost = twilio_obj.all_llm_costs.simple_conversation

	if (
			not twilio_obj.has_metered_subscription and
			user_total_available_credits < min_cost
	):
		logger.error(
			f"User {twilio_obj.username} does not have enough "
			f"credits to cover the cost of the simple conversation."
		)
		send_whatsapp_message(
			to_phone_number=twilio_obj.phone_number,
			body=settings.NOT_ENOUGH_CREDITS_MSG
		)
		
		return JSONResponse(status_code=200, content={"message": "Success"})

	logger.error("twilio_obj: " + str(twilio_obj.model_dump()))
	media_file_link = None
	if twilio_obj.media_url:
		try:
			media_file_link = process_media_url(twilio_publisher_msg=twilio_obj)
			logger.error(f"media_file_link: {media_file_link}")
			if media_file_link:
				twilio_obj.msg += settings.MEDIA_FILE_HUMAN_MSG_FORMAT.format(
					file_content_type=twilio_obj.media_type,
					media_file_link=media_file_link,
				)
				
				logger.error(f"twilio_obj.msg: {twilio_obj.msg}")
		except Exception as e:
			logger.error(
				f"User {twilio_obj.username} encountered an error when "
				f"processing the media file. Error: {e}"
			)
			send_whatsapp_message(
				to_phone_number=twilio_obj.phone_number,
				body=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT
			)
			return JSONResponse(status_code=200, content={"message": "Success"})
			
	user_db_msgs = update_user_msgs(  # write the user message to the db
		username=twilio_obj.username, user_msg=twilio_obj.msg,
		timestamp=twilio_obj.timestamp, user_is_first=True
	)

	llm_response = call_main_supervisor(  # call the llm agent
		messages=[(msg["role"], msg["content"]) for msg in user_db_msgs["msgs"]],
		twilio_publisher_msg=twilio_obj, media_file_link=media_file_link,
		user_total_available_credits=user_total_available_credits,
		has_metered_subscription=twilio_obj.has_metered_subscription,
		
	)
	
	if llm_response.is_error:
		send_whatsapp_message(
			to_phone_number=twilio_obj.phone_number,
			body=llm_response.message,
		)
		return JSONResponse(status_code=200, content={"message": "Success"})
	
	consume_user_credits(
		username=twilio_obj.username,
		call_cost=llm_response.total_call_cost,
		current_date=datetime.now().strftime("%d-%m-%Y"),
		timestamp=twilio_obj.timestamp,
		api_name=API_NAME,
		has_metered_subscription=twilio_obj.has_metered_subscription
	)

	update_user_msgs(  # update the user messages with the assistant response
		username=twilio_obj.username, assistant_msg=llm_response.message,
		timestamp=int(datetime.now().timestamp()), user_is_first=False
	)

	twilio_msgs = split_on_symbols(text=llm_response.message)
	
	for m in twilio_msgs:
		send_whatsapp_message(
			to_phone_number=twilio_obj.phone_number,
			body=m
		)
		time.sleep(0.5)

	return JSONResponse(status_code=200, content={"message": "Success"})
