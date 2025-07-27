import logging
from typing import Literal

import yfinance as yf
import pandas as pd
from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from llm_graph.utils.conversations_state import State
from llm_graph.utils.translation import translate
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.sub_graphs.stocks.stock_helper import (
	get_stock_symbol_chain, get_stock_symbol_format_instructions
)


logger = logging.getLogger("APP_AI_V1_" + __name__)


def get_financial_health(stock_symbol: str, ) -> str:
	"""
	Get the latest financial health information for a given stock symbol.
	Provide the stock symbol as the input to this tool.
	"""
	stock_symbol = stock_symbol.upper()
	stock_symbol = stock_symbol.replace(" ", "")
	stock_symbol = stock_symbol.strip()
	stock_symbol = stock_symbol.replace(".", "-")
	try:
		ticker = yf.Ticker(stock_symbol)

		df = ticker.get_income_stmt(as_dict=False, freq="quarterly")
		if isinstance(df.columns[0], pd.Timestamp):
			df.columns = df.columns.strftime('%Y-%m-%d')
		income_statement = df.to_dict(orient='index')

		df = ticker.get_balance_sheet(as_dict=False, freq="quarterly")
		if isinstance(df.columns[0], pd.Timestamp):
			df.columns = df.columns.strftime('%Y-%m-%d')
		balance_sheet = df.to_dict(orient='index')

		df = ticker.get_cash_flow(as_dict=False, freq="quarterly")
		if isinstance(df.columns[0], pd.Timestamp):
			df.columns = df.columns.strftime('%Y-%m-%d')
		cash_flow = df.to_dict(orient='index')

		return str(
			{
				"income_statement": income_statement,
				"balance_sheet": balance_sheet,
				"cash_flow": cash_flow,
			}
		) + "SUCCESS"

	except Exception as e:
		logger.error(
			f"Error getting financial health for stock symbol {stock_symbol}: {e}"
		)
		return (
			"Sorry, I could not find any financial health information "
			"for the stock symbol you provided."
		)


financial_health_template = PromptTemplate(
	input_variables=["financial_health", "new_message", "history", "language"],
	template="""
	You are a helpful AI stock financial health analyst.
	Your job is to understand the user's query and the financial health
	information for the stock symbol.

	This is the user new message:
	{new_message}

	This is the financial health information:
	"{financial_health}"

	This is the conversation history so far:
	{history}

	Interpret for the user the financial health information and
	provide it to the user. Do not make it to short or too long. Make it just 
	right.

	Do not be very technical. Make it easy to understand for the user. Be
	technical only if the user asks for it.

	Try to engage the user in another conversation. 

	If not part of the conversation history you can inform the user that you 
	can offer the following additional services:
	- Stock news
	- Stock earnings and forecasting
	- Historical trends
	- Market sentiment information
	- In-depth stock analysis for one specific stock
	- Web search for general stock news and trends or in depth information
	about a specific stock.

	YOU MUST End every response with informing the user that the information 
	provided is not financial advice.
	
	Max response length 500 words.
	Respond in the language {language}.
	"""
)

financial_health_chain = financial_health_template | base_llm_vertexai


def financial_health_node(
		state: State
) -> Command[Literal["financial_health_node"]]:
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
	
	extraction_result = financial_health_chain.invoke(
		{
			"new_message": str(new_message),
			"financial_health": get_financial_health(
				dict_response.get("stock_symbol")
			),
			"history": str(history),
			"language": language,
		}
	)

	return Command(
		update={
			"messages": [
				AIMessage(
					content=extraction_result.content,
					name="financial_health_node"
				)
			]
		},
		goto=END,
	)
