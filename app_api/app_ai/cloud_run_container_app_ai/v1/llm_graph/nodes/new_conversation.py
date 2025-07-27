from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from core import settings
from langchain_core.prompts import PromptTemplate
from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import delete_user_msg_history
from llm_graph.utils.other import get_historical_and_new_msg
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


conv_just_started_prompt_template = PromptTemplate(
	input_variables=["history", "new_message", "services", "language"],
	template="""
			You AI assistant. Read the conversation history, the 
			latest user message and the list of services you can provide 
			and respond accordingly. Be polite and helpful.

			Conversation history:
			{history}

			Latest user message:
			{new_message}

			You currently offer the following services:
			{services}

			Respond in the language {language}
			"""
)

initial_response_chain = conv_just_started_prompt_template | base_llm_vertexai

evaluate_conv_prompt_template = PromptTemplate(
		input_variables=["history", "new_message", "services", "language"],
		template="""
			You are an AI decision maker. You will receive the entire 
			conversation history and the latest user message. Your job:
			
			1) Determine if the latest user message is the start of a new
			conversation. A new conversation might be the user saying 
			something like "let's start over" or the user switching topics
			completely and is not related to the previous conversation.
			Only consider the last user message based on the conversation history.

			2) Provide a short message ("response") that you would send to 
			the user next to acknowledge the new conversation.

			Rules:
			- Output valid JSON ONLY with these keys: "is_new_conversation" and
			"response".
			- "is_new_conversation" is a boolean (true or false).
			- "response" is the text you would respond with to the user right
			now. Respond in the language {language}

			Conversation so history:
			{history}

			Latest user message:
			{new_message}

			You currently only offer the following services:
			{services}			
		"""
	)

response_schemas = [
		ResponseSchema(
			name="is_new_conversation", type="bool",
			description=(
				"True if a totally new conversation is requested else False"
			)
		),
		ResponseSchema(
			name="response", type="str",
			description="The response to the user in the language {language}"
		),
	]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

evaluate_conv_chain = (
		evaluate_conv_prompt_template | base_llm_vertexai | output_parser
)


def new_conversation_node(
		state: State
) -> Command[Literal["new_conversation_node"]]:
	language = state.get("language", "english")

	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	services = settings.LIST_OF_SERVICES_WE_PROVIDE

	if (  # the conversation just started
			len(state.get("messages", [])) <= 2 and
			state.get("messages", [])[0].type == "ai"
	):

		extraction_result = initial_response_chain.invoke(
			{
				"history": history,
				"new_message": new_message,
				"services": services,
				"language": language
			}
		)

		return Command(
			update={
				"messages": [
					AIMessage(
						content=extraction_result.content,
						name="new_conversation_node"
					)
				],
			},
			goto=END,
		)

	json_resp = evaluate_conv_chain.invoke(
		{
			"history": history,
			"new_message": new_message,
			"services": services,
			"language": language
		}
	)
	if json_resp.get("is_new_conversation") and json_resp.get("response"):
		resp = json_resp.get("response")
		if state.get("username"):
			delete_user_msg_history(username=state.get("username"))
		
	elif not json_resp.get("is_new_conversation") and json_resp.get("response"):
		resp = json_resp.get("response")
	else:
		resp = translate(
			msg=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT,
			language=language
		)

	return Command(
		update={
			"messages": [
				AIMessage(
					content=resp, name="new_conversation_node"
				)
			]
		},
		goto=END
	)
