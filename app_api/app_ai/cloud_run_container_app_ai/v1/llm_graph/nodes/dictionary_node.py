from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from langchain_core.prompts import PromptTemplate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg


dict_and_spelling_template = PromptTemplate(
	input_variables=["history", "new_message", "language"],
	template="""
			You are an AI assistant that helps the user by explaining
			different terms or concepts. You can also help the user with spelling.
			
			If the user asks how to correctly spell a word, or a phrase,
			provide the correct word or phrase. Do not rephrase the word or
			phrase only correct the spelling.
			
			If the user asks for the meaning of a word or phrase, provide
			the meaning of the word or phrase, and a few examples how it's used.
			
			If you determine from the conversation context that the user still
			does not understand the term or concept, provide a simpler
			explanation each time simplifying the explanation until the user
			understands.

			Conversation history:
			{history}

			Latest user message:
			{new_message}

			Max response length is 300 words.
			Respond in the language {language}
			"""
)

dict_and_spelling_chain = dict_and_spelling_template | base_llm_vertexai


def dictionary_and_spelling_node(
		state: State
) -> Command[Literal["dictionary_and_spelling_node"]]:
	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	
	extraction_result = dict_and_spelling_chain.invoke(
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
					name="dictionary_and_spelling_node"
				)
			],
		},
		goto=END,
	)
