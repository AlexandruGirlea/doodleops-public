import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, SystemMessage

from llm_graph.utils.conversations_state import State
from llm_graph.utils.web_search import search_google
from llm_graph.utils.llm_models import base_llm_vertexai

logger = logging.getLogger("APP_AI_V1_" + __name__)

googl_search_agent = create_react_agent(
	model=base_llm_vertexai, tools=[search_google]
)


def web_search_node(
		state: State
) -> Command[Literal["web_search_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")
	
	state["messages"] = [
		SystemMessage(
			content=f"""
				You are a helpful career google search assistant.

				You job is to understand the conversation context, formulate the
				best google search query that will help the user find the career
				resources he is looking for. Ex: jobs, training programs, etc.
				
				In the query do not include any salary expectation or job specific
				terms, because it will affect the search results. You should try
				to formulate a general search query for career resources needed.
				For example if it's a job search do something like this:
				- jobs `profession name` `location'
				If it's a training program search do something like this:
				- `profession name` training program `type` `location`
				- `profession name` training program `name` `location`
				
				Use the above examples to get the idea of how to formulate the
				search query. Being too specific like salary expectation or
				training program cost will not return the best results.

				VERY IMPORTANT: YOU as the assistant should formulate a search
				query for google that is most likely to return links that the
				user needs.
				The query YOU formulate should not include any special characters.
				Only use alphanumeric characters and spaces.
				It does not matter if the user provides a query, you
				should always formulate a search query based on the conversation.

				If no location is provided in the conversation context, presume
				the location is the country that speaks the language of user
				conversation. If no location and language is associated with
				multiple countries (ex: spanish) DO NOT call the tool, ask the
				user for the location where to search, politely and end the
				conversation there, because you are an international assistant.

				If you have what you need call `search_google` tool to do the
				search.

				Very important information to consider when calling the tool:
				If it's clear where the user is looking to find a job,
				ex: France, Japan, etc. You should change all these parameters
				`host_language_code`, `language_restrict`, `geolocation` to the
				country and language values. We want to search for the career
				resources the user wants, in the native language of the country.
				Also the Query should be in the language of the country.

				Example for France:
				- `query`: recherche d'une opportunité d'emploi
				- `host_language_code`: fr
				- `language_restrict`: lang_fr
				- `geolocation`: fr

				Example for USA:
				- `query`: looking for a job opportunity
				- `host_language_code`: en
				- `language_restrict`: lang_en
				- `geolocation`: us

				for `language_restrict` you can search in multiple languages
				as well by using the pipe `|` Example: `lang_zh-TW|lang_zh-CN`

				And you will respond with bullet points of the search results
				like this:
				- Title (Url) - Snippet
				- Title (Url) - Snippet

				If `search_google` tool response is useful, you should respond
				with the formatted response, make sure to include only links that
				point to career resources the user is looking for. DO NOT provide
				results that include links to social media, forums, etc. If you
				did not get a useful response from the tool, you should try to
				respond to the best of your knowledge.

				In your final response only use *italics*, **bold**,
				and ```monospace``` as needed with Markdown syntax, but do not use
				other Markdown elements (e.g., links). Include URLs as plain text
				(e.g., https://example.com) without formatting.
				
				Max response length is 300 words.
				Respond in the language: {language} but do not alter any
				of the links or snippets you get from the tool.
				"""
				)
			] + state["messages"]
	
	result = googl_search_agent.invoke({"messages": state["messages"]})
	
	return Command(
		update={"messages": [
			AIMessage(
				content=result["messages"][-1].content,
				name="web_search_node",
				additional_kwargs={"web_search": all_llm_costs.web_search}
			)
		]},
		goto=END
	)
