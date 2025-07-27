from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from langchain_core.prompts import PromptTemplate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg

health_template = PromptTemplate(
	input_variables=["history", "new_message", "language"],
	template="""
			You are an AI Health and Psychology assistant. 
			Your job is to understand what the user needs and only inform
			the user that you can't provide any medical advice, and that the user
			should consult a professional.
			
			VERY IMPORTANT, DO NOT provide or facilitate any medical or
			psychological advice, maybe the user just wants to talk because of
			depression. You can't offer that yet so politely and safely decline.

			Conversation history:
			{history}

			Latest user message:
			{new_message}

			Max response length is 300 words.
			Respond in the language {language}
			"""
)


health_chain = health_template | base_llm_vertexai


def health_node(
		state: State
) -> Command[Literal["health_node"]]:
	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	
	extraction_result = health_chain.invoke(
		{
			"history": history,
			"new_message": new_message,
			"language": state.get("language", "english")
		}
	)
	
	return Command(
		update={
			"messages": [
				AIMessage(
					content=extraction_result.content,
					name="health_node"
				)
			],
		},
		goto=END,
	)
