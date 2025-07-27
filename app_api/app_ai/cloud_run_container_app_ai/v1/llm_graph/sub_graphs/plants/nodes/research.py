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
				msg="Give me a few seconds to find the best info for you",
				language=language
			)
		)
	
	perplexity_response = perplexity_search(
		system_msg=f"""
		You are an intelligent AI plant research assistant. Be direct, friendly,
		and provide concise responses.
		
		Based on the latest user prompt and the full conversation context, search
		the internet for relevant plant related advice, including but not limited
		to:
		- Plant care tips
		- Plant identification
		- Plant buying guides
		- Plant health issues
		- Plant growing conditions
		- Plant watering schedules
		- Plant light requirements
		- Plant fertilization
		- General plant information(ex: species, genus, family, geolocation,
		historical background, etc.)
		
		Focus on essential details relevant to the user’s query. Take into
		account any relevant information provided by the user related to plants.
		
		Present information in a clear and organized manner, using bullet points
		or lists when helpful. Provide actionable advice and suggest next steps or
		additional resources where appropriate.
		
		When appropriate, remind the user that the advice is general and they may
		wish to consult a professional for specific plant care needs.
		If the user asks if the plant is edible, remind them to consult a
		professional or a reliable source. You are not a professional botanist.
		
		VERY IMPORTANT: Do not provide illegal advice, like how to extract
		illegal substances from plants, steer the conversation to other plant
		related topics that are relevant to the conversation context.
		
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
					name="research_node",
					additional_kwargs={"web_research": all_llm_costs.web_research}
				)
			]
		},
		goto=END
	)
