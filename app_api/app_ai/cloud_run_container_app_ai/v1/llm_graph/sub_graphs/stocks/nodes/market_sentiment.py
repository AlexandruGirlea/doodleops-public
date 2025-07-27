import logging
from typing import Literal

import yfinance as yf
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


logger = logging.getLogger("APP_AI_V1_" + __name__)


def get_market_sentiment(stock_symbol: str, ) -> str:
	"""
	Get the market sentiment information for a given stock symbol.
	Provide the stock symbol as the input to this tool.
	
	Example: "AAPL"
	"""
	stock_symbol = stock_symbol.upper()
	stock_symbol = stock_symbol.replace(" ", "")
	stock_symbol = stock_symbol.replace(".", "-")
	try:
		ticker = yf.Ticker(stock_symbol)

		df = ticker.get_recommendations()
		recommendations = df.to_dict(orient='records')
		analyst_price_targets = ticker.get_analyst_price_targets()

		df = ticker.get_upgrades_downgrades()
		df.index = df.index.normalize()
		latest_date = df.index.max()
		latest_recs = df.loc[[latest_date]]
		latest_recs.index.name = 'GradeDate'
		df_reset = latest_recs.reset_index()
		df_reset['GradeDate'] = df_reset['GradeDate'].dt.strftime('%Y-%m-%d')
		latest_upgrades_downgrades = df_reset.to_dict(orient='records')

		return str(
			{
				"recommendations": recommendations,
				"analyst_price_targets": analyst_price_targets,
				"latest_upgrades_downgrades": latest_upgrades_downgrades,
			}
		) + "SUCCESS"

	except Exception as e:
		logger.error(
			f"Error getting market sentiment for stock symbol {stock_symbol}: {e}"
		)
		return (
			"Sorry, I could not find any market sentiment information "
			"for the stock symbol you provided."
		)


market_sentiment_template = PromptTemplate(
	input_variables=["market_sentiment", "new_message", "history", "language"],
	template="""
		You are a helpful AI stock market sentiment analyst.
		Your job is to understand the user's query and the latest
		market sentiment information for the stock symbol.

		This is the user new message:
		{new_message}

		This is the market sentiment information:
		"{market_sentiment}"

		This is the conversation history so far:
		{history}

		Interpret for the user the market sentiment information and
		provide it to the user. Do not make it to short or too long. Make it just 
		right. But you still have to add the institution names who provided the
		recommendations and the target prices.

		Try to engage the user in another conversation. 

		If not part of the conversation history you can inform the user that you 
		can offer the following additional services:
		- Stock news
		- Stock financial health
		- Historical trends
		- Stock earnings and forecasting
		- In-depth stock analysis for one specific stock
		- Web search for general stock news and trends or in depth information
		about a specific stock.

		YOU MUST End every response with informing the user that the information 
		provided is not financial advice.

		Respond in the language {language} and keep the response under
		3000 characters.
		"""
)

market_sentiment_chain = market_sentiment_template | base_llm_vertexai


def market_sentiment_node(
		state: State
) -> Command[Literal["market_sentiment_node"]]:
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

	extraction_result = market_sentiment_chain.invoke(
		{
			"new_message": str(new_message),
			"market_sentiment": get_market_sentiment(stock_symbol),
			"history": str(history),
			"language": language,
		}
	)

	return Command(
		update={
			"messages": [
				AIMessage(
					content=extraction_result.content,
					name="market_sentiment_node"
				)
			]
		},
		goto=END,
	)
