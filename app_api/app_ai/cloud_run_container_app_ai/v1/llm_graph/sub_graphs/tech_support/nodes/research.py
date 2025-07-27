import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from llm_graph.utils.translation import translate
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.web_search import perplexity_search

logger = logging.getLogger("APP_AI_V1_"+__name__)


def research_node(state: State) -> Command[Literal["research_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds research the best info for you",
				language=language
			)
		)
	
	perplexity_response = perplexity_search(
		system_msg=f"""
		You are an AI Tech agent. Be direct, friendly, and provide concise
		responses.
		
		Based on the latest user prompt and the full conversation context, search
		the internet to help the user in his tech journey. Try to help the user
		with what he needs, for example:
		- code suggestions to fix a bug
		- device settings to turn on/off a feature
		or any other tech related help the user needs.
		
		Focus on essential details relevant to the user’s query. Take into
		account any relevant information provided by the user.
		
		Present information in a clear and organized manner, using bullet points
		or lists when helpful. Provide actionable advice and suggest next steps or
		additional resources where appropriate.
		
		VERY IMPORTANT: Do not provide illegal advice.
		
		Max response length is 300 words.
		Respond in the language {language}.
		""",
		conversation=state["messages"],
		model="sonar-pro",
		language=language,
	)
	
	return Command(
		update={
			"messages": [
				AIMessage(
					content=perplexity_response,
					additional_kwargs={"web_research": all_llm_costs.web_research}
				)
			]
		},
		goto=END
	)
