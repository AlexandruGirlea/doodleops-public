import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.web_search import perplexity_search

logger = logging.getLogger("APP_AI_V1_" + __name__)


def research_node(state: State) -> Command[Literal["research_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")

	# inform the user that we are searching
	if state.get("user_phone_number"):
		wait_msg = (
			"Give me a few seconds to find the best stock information for you."
		)
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(msg=wait_msg, language=language)
		)
	
	perplexity_response = perplexity_search(
		system_msg=f"""
				You are an intelligent AI stock assistant.

				Your main goal is to provide the user with the best stock
				information available on the web.

				Focus on the key details (stock symbols, company names,
				trends and general stock information within the user's
				query) without overloading the prompt with peripheral
				instructions. Provide only the most relevant information.

				ONLY search for information on reputable websites and avoid
				potential harmful websites.
				
				The last messages in the conversation are the most important for
				context.
				
				Respond in the language {language}. Max 400 tokens long.
		""",
		conversation=state["messages"],
		model="sonar-pro",
		language=language,
	)
	
	return Command(
		update={"messages": [
			AIMessage(
				content=perplexity_response,
				additional_kwargs={"web_research": all_llm_costs.web_research}
				)
			]
		},
		goto=END
	)
