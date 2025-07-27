import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, SystemMessage

from common.pub_sub_schema import LLMCost
from llm_graph.utils.conversations_state import State
from llm_graph.utils.web_search import search_google
from llm_graph.utils.llm_models import base_llm_vertexai


logger = logging.getLogger("APP_AI_V1_"+__name__)


googl_search_agent = create_react_agent(
	model=base_llm_vertexai, tools=[search_google]
)


def web_search_node(state: State) -> Command[Literal["web_search_node"]]:
	language = state.get("language", "english")
	all_llm_costs: LLMCost = state.get("all_llm_costs")
	
	state["messages"] = [
		SystemMessage(
			content=f"""
				You are a helpful shopping and selling google search assistant.
				
				You job is to understand the conversation context, formulate the
				best google search query that will help the user find the store
				where the user can buy or sell what he is looking for.
				
				In the query do not include any price information or to much data.
				Google search query do not work well with very specific long
				queries and might not return any results.
				Try to use queries like this:
				- buy `product name` `location`
				- shop `product name` `location`
				- stores `product name` `location`
				- sell `product name` `location`
				or if the user is looking for a specific product like a phone
				- buy `product name` `brand` `location`
				- shop `product name` `type` `location`
				only if the user insists include a technical specification like
				- buy `product name` `brand` `model` `location`
				but don't do this for selling. For selling only use the product
				type and location.
				
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
				user for the location where to search politely and end the
				conversation there, because you are an international assistant.
				
				If you have what you need call `search_google` tool to do the
				search.
				
				Very important information to consider when calling the tool:
				If it's clear where the user is looking to buy the product,
				ex: France, Japan, etc. You should change all these parameters
				`host_language_code`, `language_restrict`, `geolocation` to the
				country and language values. We want to search for the products
				or locations the user wants, in the native language of the
				country.
				Also the Query should be in the language of the country.
				
				Example for France:
				- `query`: à la recherche d'un produit
				- `host_language_code`: fr
				- `language_restrict`: lang_fr
				- `geolocation`: fr
				
				Example for USA:
				- `query`: looking for a product
				- `host_language_code`: en
				- `language_restrict`: lang_en
				- `geolocation`: us
				
				for `language_restrict` you can search in multiple languages
				as well by using the pipe `|` Example: `lang_zh-TW|lang_zh-CN`
				
				You will respond to the user with bullet points of the search
				results like this:
				- Title (Url) - Snippet summary
				- Title (Url) - Snippet summary
				
				If `search_google` tool response is useful, you should respond
				with the formatted response, make sure to include only useful
				links based on the user's needs.
				
				DO NOT provide results that include links to social media
				(like Facebook, Twitter, Instagram), forums(like Reddit, Quora),
				documents, or other non shop related links. If you did not get a
				useful response from the tool, you should try to respond to the
				best of your knowledge.
				
				In your final response only use *italics*, **bold**,
				and ```monospace``` as needed with Markdown syntax, but do not use
				other Markdown elements (e.g., links). Include URLs as plain text
				(e.g., https://example.com) without formatting.
				
				Respond in the language: {language}.
				"""
		)
	] + state["messages"]
	
	result = googl_search_agent.invoke({"messages": state["messages"]})
	
	return Command(
		update={"messages": [
			AIMessage(
				name="web_search_node",
				content=result["messages"][-1].content,
				additional_kwargs={"web_search": all_llm_costs.web_search}
			)
		]},
		goto=END
	)
