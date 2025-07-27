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
				msg="Give me a few seconds to research the best info for you",
				language=language
			)
		)
	
	perplexity_response = perplexity_search(
		system_msg=f"""
		You are an AI Events Agent. Be direct, friendly, and provide concise
		responses.
		
		Based on the latest user prompt and the full conversation context, search
		the internet to help with his events related needs. Provide relevant
		information on topics such as (but not limited to):
		- what events are happening in the user's area
		- how to organize an event
		- information about concerts, festivals, etc.
		- how to get tickets for events
		and other events related topics.
		
		Focus on essential details relevant to the user’s query. Take into
		account any relevant information provided by the user.
		
		Present information in a clear and organized manner, using bullet points
		or lists when helpful. Provide actionable advice and suggest next steps or
		additional resources where appropriate.
		
		VERY IMPORTANT: Do not provide illegal advice.
		If the user needs help with something that is potentially dangerous,
		tell the user to consult a professional. You are an AI
		assistant that can make mistakes.
		
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
