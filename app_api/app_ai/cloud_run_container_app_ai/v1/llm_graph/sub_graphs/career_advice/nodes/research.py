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
		You are an intelligent career research assistant. Be direct, friendly, and
		provide concise responses.
		
		Based on the latest user prompt and the full conversation context, search
		the internet for relevant career advice, including but not limited to:
		- Concise career path recommendations with key aspects: skills, education
		and opportunities.
		- Advice tailored to the user’s career interests and goals as expressed in
		the conversation.
		- Salary expectations for specific roles.
		- Company reviews and culture.
		- Job market trends and growth opportunities.
		- Certification or training programs.
		- Guidance on achieving career goals.
		- Industry-specific advice and trends.
		- Future job market outlooks.
		- Most asked questions in job interviews and how to answer them based on
		the user’s career interests.
		
		Do not search for specific jobs openings unless the user provides a
		location.
		
		Focus on essential details relevant to the user’s query. Take into
		account any relevant information provided by the user, such as education,
		experience or location.
		
		Present information in a clear and organized manner, using bullet points
		or lists when helpful. Provide actionable advice and suggest next steps or
		additional resources where appropriate.
		
		When appropriate, remind the user that the advice is general and they may
		wish to consult a career counselor or other professional for personalized
		guidance.
		
		VERY IMPORTANT: Do not provide illegal or unlicensed professional advice.
		Do not encourage unethical behavior or child exploitation.
		
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
					name="research_node",
					additional_kwargs={"web_research": all_llm_costs.web_research}
				)
			]
		},
		goto=END
	)
