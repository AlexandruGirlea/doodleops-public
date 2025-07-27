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


def get_earnings_and_forecasting(stock_symbol: str, ) -> str:
	"""
	Get the latest earnings and forecasting information for a given stock symbol.
	Provide the stock symbol as the input to this tool.
	
	Example: "AAPL"
	"""
	stock_symbol = stock_symbol.upper()
	stock_symbol = stock_symbol.replace(" ", "")
	stock_symbol = stock_symbol.strip()
	stock_symbol = stock_symbol.replace(".", "-")
	try:
		ticker = yf.Ticker(stock_symbol)

		df = ticker.get_earnings_history()
		df.index.name = 'quarter'
		df_reset = df.reset_index()
		df_reset['quarter'] = df_reset['quarter'].dt.strftime('%Y-%m-%d')
		earnings_per_share_actual_vs_estimated = df_reset.to_dict(
			orient='records'
		)

		df = ticker.get_earnings_dates()
		df.index.name = 'Earnings Date'
		df_reset = df.reset_index()
		df_reset['Earnings Date'] = df_reset['Earnings Date'].dt.strftime(
			'%Y-%m-%d'
		)
		earnings_dates = df_reset.to_dict(orient='records')

		df = ticker.get_earnings_estimate()
		df.index.name = 'period'
		df_reset = df.reset_index()
		earnings_estimate = df_reset.to_dict(orient='records')

		df = ticker.get_eps_trend()
		df.index.name = 'period'
		df_reset = df.reset_index()
		earnings_per_share_trend = df_reset.to_dict(orient='records')

		df = ticker.get_growth_estimates()
		df.index.name = 'period'
		df_reset = df.reset_index()
		growth_estimates = df_reset.to_dict(orient='records')

		df = ticker.get_revenue_estimate()
		df.index.name = 'period'
		df_reset = df.reset_index()
		revenue_estimate = df_reset.to_dict(orient='records')

		return str(
			{
				"earnings_per_share_actual_vs_estimated": (
					earnings_per_share_actual_vs_estimated
				),
				"earnings_dates": earnings_dates,
				"earnings_estimate": earnings_estimate,
				"earnings_per_share_trend": earnings_per_share_trend,
				"growth_estimates": growth_estimates,
				"revenue_estimate": revenue_estimate,
				"calendar": ticker.get_calendar()
			}
		) + "SUCCESS"

	except Exception as e:
		logger.error(f"Error getting forcast for stock symbol {stock_symbol}: {e}")
		return (
			"Sorry, I could not find any earnings and forecasting information "
			"for the stock symbol you provided."
		)


earnings_and_forecasting_template = PromptTemplate(
	input_variables=[
		"earnings_and_forecasting", "new_message", "history", "language"
	],
	template="""
		You are a helpful AI stock earnings and forecasting analyst.
		Your job is to understand the user's query and the latest earnings and
		forecasting information for the stock symbol.

		This is the user new message:
		{new_message}

		This is the earnings and forecasting information:
		"{earnings_and_forecasting}"

		This is the conversation history so far:
		{history}

		Interpret for the user the earnings and forecasting
		information and provide it to the user. Do not make it to short or too 
		long. Make it just right.

		Do not be very technical. Make it easy to understand for the user. Be
		technical only if the user asks for it.

		Try to engage the user in another conversation. 

		If not part of the conversation history you can inform the user that you 
		can offer the following additional services:
		- Stock news
		- Stock financial health
		- Historical trends
		- Market sentiment information
		- In-depth stock analysis for one specific stock
		- Web search for general stock news and trends or in depth information
		about a specific stock.

		YOU MUST End every response with informing the user that the information 
		provided is not financial advice.

		Max response length is 500 words.
		Respond in the language {language}.
		"""
)

earnings_and_forecasting_chain = (
	earnings_and_forecasting_template | base_llm_vertexai
)


def earnings_and_forecasting_node(
		state: State
) -> Command[Literal["earnings_and_forecasting_node"]]:
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
	result = get_earnings_and_forecasting(stock_symbol)

	extraction_result = earnings_and_forecasting_chain.invoke(
		{
			"new_message": str(new_message),
			"earnings_and_forecasting": result,
			"history": str(history),
			"language": language,
		}
	)

	return Command(
		update={
			"messages": [
				AIMessage(
					content=extraction_result.content,
					name="earnings_and_forecasting_node"
				)
			]
		},
		goto=END,
	)
