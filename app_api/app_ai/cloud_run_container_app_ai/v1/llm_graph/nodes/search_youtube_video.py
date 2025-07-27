import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.web_search import youtube_search
from llm_graph.utils.llm_models import lite_llm_vertexai, base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg

logger = logging.getLogger("APP_AI_V1_" + __name__)

response_schemas = [
	ResponseSchema(
		name="call_youtube", type="bool",
		description=(
			"Set to *True* if you think that you understand what to look for on "
			"youtube. Set to *False* if you need more information before you can "
			"create a `youtube_query` for the user"
		)
	),
	ResponseSchema(
		name="youtube_query", type="str",
		description=(
			"If `call_youtube` is *True*, provide a youtube query in this field. "
			"This is the query that you as the AI think is most likely to return "
			"the best results for the user when he does a youtube search."
			"Pay attention to the conversation context and try to choose the best "
			"language to formulate the query in. This is the user language "
			"{language} or use english, which ever is more appropriate."
		)
	),
	ResponseSchema(
		name="user_response", type="str",
		description=(
			"If `call_youtube` is *False* provide a response to the user that "
			"you need more information to create before searching for videos. "
			"If `call_youtube` is *True* then this field should be empty."
		)
	),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

youtube_query_template = PromptTemplate(
	input_variables=[
		"history", "new_message", "format_instructions"
	],
	template="""
		You are a helpful AI video search assistant.
		Your single job is to look at the conversation history and the latest
		user message and identify what the user wants to search for and
		formulate the best youtube search query that will help the user find what
		he is looking for.
		
		In the query do not include to much data. Youtube search does
		not work well with very specific long queries and might not return any
		results.
			Try to use queries like this:
			- review `product name` or `product type`
			- how to fix `name of bug` on `device name`
			- unboxing `product name`
			- tutorial `product name`
			- `product name` vs `product name`
			and so on.
		
		VERY IMPORTANT: YOU as the assistant should formulate a search
		query for youtube that is most likely to return links that the
		user needs.
		
		The query YOU formulate should not include any special characters.
		Only use alphanumeric characters and spaces.
		It does not matter if the user provides a query, you
		should always formulate a search query based on the conversation.
		
		If the search doesn't need to be made, set the `call_youtube` variable to
		False and provide the `user_response` that should be sent to the user.
		
		Response format instructions:
		{format_instructions}
		
		Always return all fields in the response schema even if they are empty.
		- "call_youtube": true,
		- "youtube_query": "tutorial control center iphone",
		- "user_response": ""

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		"""
)

youtube_query_chain = youtube_query_template | lite_llm_vertexai | output_parser

response_template = PromptTemplate(
	input_variables=["history", "new_message", "language", "youtube_resp"],
	template="""
			You are a helpful AI assistant that can respond to the user
			based on the youtube videos that you found.

			Conversation history:
			{history}

			Latest user message:
			{new_message}

			Youtube videos found:
			{youtube_resp}

			Be polite and engaging.

			In your final response only use *italics*, **bold**,
			and ```monospace``` as needed with Markdown syntax, but do not use
			other Markdown elements (e.g., links). Include URLs as plain text
			(e.g., https://example.com) without formatting.

			Max response length is 400 words. Respond in the language {language}.
			"""
)

response_chain = response_template | base_llm_vertexai


def search_youtube_video_node(
		state: State) -> Command[Literal["search_youtube_video_node"]]:
	language = state.get("language", "english")
	
	messages = get_historical_and_new_msg(state=state)
	history = messages["history"]
	new_message = messages["new_message"]
	
	json_resp = youtube_query_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"format_instructions": format_instructions
		}
	)
	error_msg = ""
	if not json_resp.get("call_youtube"):
		if not json_resp.get("user_response"):
			error_msg = translate(
				msg="Sorry I could not identify what you want to search for.",
				language=language
			)
		else:  # User provided a response
			return Command(
				update={
					"messages": [AIMessage(
						name="search_youtube_video_node",
						content=translate(
							msg=json_resp.get("user_response"), language=language
						)
					)],
				},
				goto=END
			)
	else:  # AI should call youtube
		if not json_resp.get("youtube_query"):
			error_msg = translate(
				msg="Sorry I could not identify what you want to search for.",
				language=language
			)
			
	if error_msg:
		return Command(
			update={
				"messages": [AIMessage(
					name="search_youtube_video_node", content=error_msg
				)],
			},
			goto=END
		)
		
	extraction_result = response_chain.invoke(
		{
			"history": history,
			"new_message": new_message,
			"language": language,
			"youtube_resp": str(youtube_search(query=json_resp["youtube_query"]))
		}
	)
	
	return Command(
		update={
			"messages": [AIMessage(
				name="search_youtube_video_node",
				content=extraction_result.content
			)],
		},
		goto=END
	)
