from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from core import settings
from langchain_core.prompts import PromptTemplate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg


generic_media_answer_template = PromptTemplate(
	input_variables=["history", "new_message", "language", "media_services"],
	template="""
			You are an AI assistant that gets called when the user uploaded
			a media file but it's not clear what the user wants to do with it.
			
			Your job is to ask the user what they want to do with the media file.
			The question should be short like: "What do
			you want to do with this image / video / pdf / audio file?".
			
			If the user says something very short like: "what should I do and..."
			provides a image url link, you can ask: "What do you want to do with
			this image file?".
			
			Conversation history:
			{history}

			Latest user message:
			{new_message}
			
			If the user asks for a list of services you can provide, you can
			list some of these: \"{media_services}\" based on what you think
			based on the conversation context, the user might be the most
			interested in.
			
			Max response length is 200 words.
			Respond in the language {language}
			"""
)

generic_media_answer_chain = generic_media_answer_template | base_llm_vertexai


def media_interpreter_node(
		state: State
) -> Command[Literal["media_interpreter_node"]]:
	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	
	extraction_result = generic_media_answer_chain.invoke(
		{
			"history": history,
			"new_message": new_message,
			"media_services": settings.LIST_OF_MEDIA_INTERPRETER_SERVICES,
			"language": state.get("language", "english")
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
