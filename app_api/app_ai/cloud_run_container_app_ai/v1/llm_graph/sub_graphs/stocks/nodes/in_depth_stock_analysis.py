import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.sub_graphs.stocks.stock_helper import (
	get_stock_symbol_chain, get_stock_symbol_format_instructions
)
from llm_graph.sub_graphs.stocks.nodes.general_info import (
	get_general_info_one_stock
)
from llm_graph.sub_graphs.stocks.nodes.earnings_and_forecasting import (
	get_earnings_and_forecasting
)
from llm_graph.sub_graphs.stocks.nodes.financial_health import (
	get_financial_health
)
from llm_graph.sub_graphs.stocks.nodes.historical_trends_and_price_data import (
	get_historical_trends_and_price_data
)
from llm_graph.sub_graphs.stocks.nodes.market_sentiment import (
	get_market_sentiment
)
from llm_graph.sub_graphs.stocks.nodes.news import get_stock_news

logger = logging.getLogger("APP_AI_V1_" + __name__)


stock_analysis_template = PromptTemplate(
	input_variables=[
		"stock_symbol", "financial_health", "stock_news",
		"earnings_forecasting", "historical_trends", "market_sentiment",
		"general_info", "user_query", "history", "language"
	],
	template="""
		You are a helpful AI stock analyst. Below are the results from multiple 
		tools for the stock symbol {stock_symbol}:

		Financial Health:
		{financial_health}

		Stock News:
		{stock_news}

		Earnings and Forecasting:
		{earnings_forecasting}

		Historical Trends:
		{historical_trends}

		Market Sentiment:
		{market_sentiment}

		General Information:
		{general_info}

		Additionally, here is the user's query:
		{user_query}

		And the conversation history so far:
		{history}

		Please provide a clear, concise analysis that synthesizes all of the 
		above types of information, ensuring the answer is understandable.
		Do not make it to short or too long. Make it just right.

		Do not be very technical. Make it easy to understand for the user. Be
		technical only if the user asks for it.

		YOU MUST end your response with a disclaimer that this is not financial 
		advice.
		
		Max response length is 600 words.
		Response in the language {language}.
		"""
)

stock_analysis_chain = stock_analysis_template | base_llm_vertexai


def in_depth_stock_analysis_node(
		state: State
) -> Command[Literal["in_depth_stock_analysis_node"]]:
	language = state.get("language", "english")
	
	messages = get_historical_and_new_msg(state=state)
	user_query = messages["new_message"]
	history = messages["history"]

	dict_response = get_stock_symbol_chain.invoke(
		{
			"history": str(history), "new_message": str(user_query),
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

	stock_symbol = dict_response["stock_symbol"]

	financial_health = get_financial_health(stock_symbol)
	stock_news = get_stock_news(stock_symbol)
	earnings_forecasting = get_earnings_and_forecasting(stock_symbol)
	historical_trends = get_historical_trends_and_price_data.invoke(
		{"stock_symbol": stock_symbol}
	)
	market_sentiment = get_market_sentiment(stock_symbol)
	general_info = get_general_info_one_stock.invoke(
		{"stock_symbol": stock_symbol}
	)

	deep_stock_analysis = {}

	if financial_health.endswith("SUCCESS"):
		deep_stock_analysis["financial_health"] = financial_health[:-7]
	if stock_news.endswith("SUCCESS"):
		deep_stock_analysis["stock_news"] = stock_news[:-7]
	if earnings_forecasting.endswith("SUCCESS"):
		deep_stock_analysis["earnings_forecasting"] = earnings_forecasting[:-7]
	if historical_trends.endswith("SUCCESS"):
		deep_stock_analysis["historical_trends"] = historical_trends[:-7]
	if market_sentiment.endswith("SUCCESS"):
		deep_stock_analysis["market_sentiment"] = market_sentiment[:-7]
	if general_info.endswith("SUCCESS"):
		deep_stock_analysis["general_info"] = general_info[:-7]
		
	if not deep_stock_analysis:
		error_msg = (
			"Sorry, I could not get the in depth stock analysis. "
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

	messages = get_historical_and_new_msg(state=state)
	user_query = messages["new_message"]
	history = messages["history"]

	extraction_result = stock_analysis_chain.invoke(
		{
			"stock_symbol": stock_symbol,
			"financial_health": deep_stock_analysis.get(
				"financial_health", "No info"
			),
			"stock_news": deep_stock_analysis.get("stock_news","No info"),
			"earnings_forecasting": deep_stock_analysis.get(
				"earnings_forecasting", "No info"
			),
			"historical_trends": deep_stock_analysis.get(
				"historical_trends", "No info"
			),
			"market_sentiment": deep_stock_analysis.get(
				"market_sentiment", "No info"
			),
			"general_info": deep_stock_analysis.get("general_info", "No info"),
			"user_query": str(user_query),
			"history": str(history),
			"language": language,
		}
	)

	return Command(
		update={
			"messages": [
				AIMessage(
					content=extraction_result.content,
					name="in_depth_stock_analysis_node"
				)
			]
		},
		goto=END,
	)
