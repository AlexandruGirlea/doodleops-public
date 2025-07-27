import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from common.pub_sub_schema import LLMCost
from llm_graph.utils.translation import translate
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.web_search import perplexity_search

logger = logging.getLogger("APP_AI_V1_" + __name__)


def research_node(state: State) -> Command[Literal["research_node"]]:
	language = state.get("language", "english")
	all_llm_costs: LLMCost = state.get("all_llm_costs")
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds to find the best options for you",
				language=language
			)
		)
	perplexity_response = perplexity_search(
		system_msg=f"""
				You are an intelligent shopping and selling research assistant.
				
				Based on the user's language try to determine the user's location
				where to search for products if not else clearly state in the
				conversation context. If not informed otherwise, you will
				assume the user is shopping or selling online and that he is in
				the USA.
				
				If no location is provided in the conversation context, presume
				the location is the country that speaks the language of the query.
				If multiple countries speak the same language, ask the user for
				the location politely.
				
				If the user is looking to buy something or needs a few options,
				provide concise, direct suggestions with up to 3 specific product
				recommendations, each with a one-sentence description and
				estimated price (e.g., 'around $X'). Include citations as [1],
				[2], etc., next to each recommendation.
				
				If the user is looking to sell something try to help him with:
				- what approximate price to sell it
				- where to sell it
				and so on.

				Focus on the key details (product specifics, relevance, and budget
				limits) without overloading the prompt with peripheral
				instructions.
				
				Else if the user is looking for more information about a product,
				provide a brief analysis, review, or specifications of the product
				he is interested in. Include the most relevant details and
				considerations that might help the user make a decision.

				If you can't find specific products, try suggesting a different
				product category or ask for additional details.

				ONLY search for products on reputable websites and avoid
				potential harmful websites.

				VERY IMPORTANT: DO NOT provide responses with content that might
				contain illegal products or services. Do not help the user
				sell something that might be illegal or harmful.

				If the user needs wants to buy something in a physical store,
				try to find the closest store to the user's location.
				If not mentioned, assume the user is shopping online.
				
				Response length max 500 characters.
				You MUST respond in the language {language}.
				""",
		conversation=state["messages"],
		model="sonar-pro",
		language=language,
	)
	return Command(
		update={
			"messages": [AIMessage(
				content=perplexity_response,
				name="research_node",
				additional_kwargs={"web_research": all_llm_costs.web_research}
			)],
		},
		goto=END
	)
