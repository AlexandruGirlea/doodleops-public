import json
import logging
from typing import Literal

import yfinance as yf
from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.sub_graphs.stocks.stock_helper import (
	get_stock_symbol_chain, get_stock_symbol_format_instructions
)


logger = logging.getLogger("APP_AI_V1_" + __name__)


def get_stock_news(stock_symbol: str) -> str:
	"""
	Get the latest news for a given stock symbol. Provide the stock symbol
	as the input to this tool.
	"""
	stock_symbol = stock_symbol.upper()
	stock_symbol = stock_symbol.replace(" ", "")
	stock_symbol = stock_symbol.strip()
	stock_symbol = stock_symbol.replace(".", "-")
	try:
		ticker = yf.Ticker(stock_symbol)
		news = ticker.get_news(tab="news")

		clean_news = []
		for n in news:
			content = n.get("content", {})
			news_object = {}
			if content.get("title"):
				news_object["title"] = content["title"]
			if content.get("description"):
				news_object["description"] = content["description"]
			if content.get("summary"):
				news_object["summary"] = content["summary"]
			if content.get("pubDate"):
				news_object["pubDate"] = content["pubDate"]
			if content.get("provider", {}).get("displayName"):
				news_object["provider"] = content["provider"]["displayName"]
			if content.get("canonicalUrl", {}).get("url"):
				news_object["news_url"] = content["canonicalUrl"]["url"]

			news_str = json.dumps(news_object)
			clean_news.append(news_str)

		calendar = ticker.get_calendar()

		return (
			f"Here are the latest news for the stock symbol {stock_symbol}: \n"
			f"News: {str(clean_news)}. \n"
			f"Calendar: {str(calendar)}."
		) + "SUCCESS"

	except Exception as e:
		logger.error(f"Error getting news for stock symbol {stock_symbol}: {e}")
		return (
			"Sorry, I could not find any news for the stock symbol you provided."
		)


stock_news_template = PromptTemplate(
	input_variables=["stock_news", "new_message", "history", "language"],
	template="""
		You are a helpful AI stock news analyst. 
		Your job is to understand the user's query and the latest news for the 
		stock symbol.

		This is the user new message:
		{new_message}

		This is the stock news:
		"{stock_news}"

		This is the conversation history so far:
		{history}

		Interpret for the user the news and provide it to the user.
		Do not make it to short or too long. Make it just right.

		Use this format to provide the news:
		- Title (pubDate): summary / description of the news (provider: url link)
		- Title (pubDate): summary / description of the news (provider: url link)
		- Title (pubDate): summary / description of the news (provider: url link)

		Try to engage the user in another conversation. 

		If not part of the conversation history you can inform the user that you 
		can offer the following additional services:
		- Stock earnings and forecasting
		- Stock financial health
		- Historical trends
		- Market sentiment information
		- Web search for general stock news and trends or in depth information
		about a specific stock.

		YOU MUST End every response with informing the user that the information 
		provided is not financial advice.

		ONLY for US stocks. If the user wants information about a non-US stock
		politely inform the user that you can only provide this type of
		information for US stocks.

		Respond in the language {language} and keep the response under
		3000 characters.
		"""
)

stock_news_chain = stock_news_template | base_llm_vertexai


def news_node(state: State) -> Command[Literal["news_node"]]:
	language = state.get("language", "english")
	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	
	dict_response = get_stock_symbol_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"format_instructions": get_stock_symbol_format_instructions
		}
	)
	
	if not dict_response.get("stock_symbol"):
		error_msg = (
			"Sorry, I could not identify the stock symbol. "
			"Please try again."
		)
		return Command(
			update={
				"messages": [
					AIMessage(
						content=translate(msg=error_msg, language=language),
						name="in_depth_stock_analysis_node"
					)
				]
			},
			goto=END,
		)
	stock_symbol = dict_response.get("stock_symbol")
	
	extraction_result = stock_news_chain.invoke(
		{
			"new_message": str(new_message),
			"stock_news": get_stock_news(stock_symbol),
			"history": str(history),
			"language": language,
		}
	)

	return Command(
		update={
			"messages": [
				AIMessage(
					content=extraction_result.content, name="news_node"
				)
			]
		},
		goto=END,
	)
