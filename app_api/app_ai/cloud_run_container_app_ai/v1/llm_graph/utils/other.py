import json
import logging

from langchain_core.messages import AIMessage, HumanMessage

from core import settings
from llm_graph.utils.conversations_state import State
from common.redis_utils import set_redis_key, get_redis_key
from common.redis_schemas import (
	REDIS_KEY_USER_WHATSAPP_MSG, REDIS_KEY_USER_PHONE_NUMBER
)


logger = logging.getLogger("APP_AI_V1_"+__name__)


def get_historical_and_new_msg(
		state: State = None, db_conversation: list = None
) -> dict:
	if not db_conversation:
		messages = [
			{
				"role": "user" if m.type == "human" else "assistant",
				"content": m.content
			}
			for m in state.get("messages", []) if m.type in {"human", "ai"}
		]
	else:
		messages = db_conversation

	return {"history": messages[:-1], "new_message": messages[-1]}


def get_user_email(user_phone_number: str) -> str:
	"""
	Get the user's email address from the Redis database using their phone number.
	"""
	value = get_redis_key(
		REDIS_KEY_USER_PHONE_NUMBER.format(number=user_phone_number)
	)

	try:
		return json.loads(value)["email"]
	except Exception as e:
		logger.error(f"Error getting user email: {e}")
		return ""


def delete_user_msg_history(username: str) -> bool:
	if not username:
		return False

	value = get_redis_key(REDIS_KEY_USER_WHATSAPP_MSG.format(username=username))
	json_value = json.loads(value)
	msgs = json_value.get("msgs", [])[-1]

	set_redis_key(
		key=REDIS_KEY_USER_WHATSAPP_MSG.format(username=username),
		simple_value=json.dumps({"msgs": [msgs]}),
		expire=60*60*24  # 1 day
	)
	return True


def convert_db_msgs_to_llm_msgs(db_msgs: list) -> list:
	llm_messages = []
	for m in db_msgs:  # transform msgs in LLMMessages
		if m[0] == "user":
			llm_messages.append(HumanMessage(content=m[1]))
		elif m[0] == "assistant":
			llm_messages.append(AIMessage(content=m[1]))
	
	return llm_messages


def process_finish_condition(
		llm_messages: list, graph_resp: State, language: str
) -> State:
	"""
	If the graph responded with a human message, this means that the AI
	did not respond to the user, so we have to force it to get a response.
	"""
	
	if not llm_messages or not graph_resp.get("messages"):
		return graph_resp
	
	if graph_resp["messages"][-1].type == "human":
		from llm_graph.nodes.new_conversation import initial_response_chain

		messages = get_historical_and_new_msg(
			state=State(messages=llm_messages)
		)
		new_message = messages["new_message"]
		history = messages["history"]
		ai_resp = initial_response_chain.invoke(
			{
				"history": history,
				"new_message": new_message,
				"services": settings.LIST_OF_SERVICES_WE_PROVIDE,
				"language": language
			}
		)
		return State(messages=[ai_resp])
	
	return graph_resp
