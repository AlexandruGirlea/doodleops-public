import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from common.pub_sub_schema import LLMCost
from llm_graph.utils.translation import translate
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.web_search import perplexity_search, youtube_search
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.nodes.search_youtube_video import (
	youtube_query_chain, format_instructions
)

logger = logging.getLogger("APP_AI_V1_" + __name__)

reviews_template = PromptTemplate(
	input_variables=[
		"history", "new_message", "language", "youtube_resp", "perplexity_resp"
	],
	template="""
			You are a helpful AI review assistant that can provide the user
			with the best reviews on products.

			Conversation history:
			{history}

			Latest user message:
			{new_message}
			
			Youtube videos found:
			{youtube_resp}
			
			Web search results:
			{perplexity_resp}
			
			When answering the user make sure to prioritize the most
			relevant information while also keeping in mind what the user
			wants. Include a mix of written and video reviews
			that you think are most relevant. Be polite and engaging.
			
			In your final response only use *italics*, **bold**,
			and ```monospace``` as needed with Markdown syntax, but do not use
			other Markdown elements (e.g., links). Include URLs as plain text
			(e.g., https://example.com) without formatting.

			Max response length is 400 words. Respond in the language {language}.
			"""
)

reviews_chain = reviews_template | base_llm_vertexai


def review_node(state: State) -> Command[Literal["review_node"]]:
	language = state.get("language", "english")
	all_llm_costs: LLMCost = state.get("all_llm_costs")
	messages = get_historical_and_new_msg(state=state)
	history = messages["history"]
	new_message = messages["new_message"]
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds to find the best options for you",
				language=language
			)
		)
	
	json_resp = youtube_query_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"format_instructions": format_instructions
		}
	)
	youtube_videos = "none found"
	if json_resp.get("youtube_query"):
		youtube_videos = youtube_search(query=json_resp["youtube_query"])
		
	if youtube_videos:
		youtube_videos = str([v.model_dump()for v in youtube_videos])
	
	perplexity_response = perplexity_search(
		system_msg=f"""
				You are an AI assistant that can help find reviews on products.

				Try to identify what is the product that the user wants a review
				on and do a research to find the best reviews on that product.
				
				Aggregating reviews from multiple sources is a good practice
				and summarize the key points of the reviews in a concise and
				clear manner.

				ONLY search for products reviews on reputable websites and avoid
				potential harmful websites.

				VERY IMPORTANT: DO NOT provide responses with content that might
				contain illegal products or services. Do not help the user
				with anything that might be illegal or harmful.

				Response length max 500 characters.
				Respond in english.
				""",
		conversation=state["messages"],
		model="sonar-pro",
		language=language,
	)
	
	extraction_result = reviews_chain.invoke(
		{
			"history": history,
			"new_message": new_message,
			"language": language,
			"perplexity_resp": perplexity_response,
			"youtube_resp": youtube_videos
		}
	)

	if perplexity_response:
		additional_kwargs = {"web_research": all_llm_costs.web_research}
	else:
		additional_kwargs = {}
	
	return Command(
		update={
			"messages": [AIMessage(
				name="review_node",
				content=extraction_result.content,
				additional_kwargs=additional_kwargs
			)],
		},
		goto=END
	)
