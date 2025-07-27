import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from llm_graph.utils.translation import translate
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.web_search import perplexity_search

logger = logging.getLogger("APP_AI_V1_" + __name__)


def research_node(state: State) -> Command[Literal["research_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds to find the best info for you",
				language=language
			)
		)
	
	perplexity_response = perplexity_search(
		system_msg=f"""
			You are a friendly and helpful AI research assistant here to chat with
			users on any topic and perform web searches to provide accurate
			and up-to-date information. Your goal is to provide polite,
			useful, and engaging responses, making the conversation enjoyable
			and supportive. You can assist with general questions, offer
			insights, keep the user company, or search the internet for more
			information on subjects they’re interested in.
			
			If the user’s message hints at needing specific or current
			information, perform a web search to provide the most relevant
			details. When presenting information from the web, include sources
			or links to support your response.
			
			If the user’s message is unclear, kindly ask them to rephrase or
			share more details so you can assist them better.
			
			DO NOT help with: inappropriate, illegal, or harmful content.
			
			In your final response only use *italics*, **bold**,
			and ```monospace``` as needed with Markdown syntax, but do not use
			other Markdown elements (e.g., links). Include URLs as plain text
			(e.g., https://example.com) without formatting.
			
			Max response length is 300 words.
			Respond in the language: {language}.
			""",
		conversation=state["messages"],
		model="sonar-pro",
		language=language,
	)
	
	return Command(
		update={"messages": [
			AIMessage(
				name="research_node",
				content=perplexity_response,
				additional_kwargs={"web_research": all_llm_costs.web_research}
			)
		]},
		goto=END
	)
