import logging
from typing import Literal

import yfinance as yf
from langgraph.graph import END
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from core import settings
from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.llm_models import base_llm_vertexai


logger = logging.getLogger("APP_AI_V1_" + __name__)

response_schemas = [
	ResponseSchema(
		name="stock_symbol", type="str",
		description=(
			"A US stock symbol like AAPL, MSFT, TSLA, etc. Only the symbol "
			"should be provided without any additional information or characters."
		)
	),
	ResponseSchema(
		name="period", type="str",
		description="""
			Period can be one of the following:
			- "1d" for 1 day
			- "5d" for 5 days
			- "1mo" for 1 month
			- "3mo" for 3 months
			- "6mo" for 6 months
			- "1y" for 1 year
			- "2y" for 2 years
			- "5y" for 5 years
			- "10y" for 10 years
			- "ytd" for year-to-date
			- "max" for maximum available data
			It has to be one of these exact values, if not the function will fail.
			Based on the conversation context choose one of these values.
	"""
	),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

historical_data_template = PromptTemplate(
	input_variables=["history", "new_message", "format_instructions"],
	template="""
		You are a helpful AI stock assistant.
		Your job is to understand the user's needs based on the conversation
		context and identify one stock symbol that the user is interested in
		and the period he wants historical trends and price data for.
		
		Period can be one of the following:
		- "1d" for 1 day
		- "5d" for 5 days
		- "1mo" for 1 month
		- "3mo" for 3 months
		- "6mo" for 6 months
		- "1y" for 1 year
		- "2y" for 2 years
		- "5y" for 5 years
		- "10y" for 10 years
		- "ytd" for year-to-date
		- "max" for maximum available data
		
		Example response can look like:
		- "stock_symbol": "AAPL" or "BRK-B"
		- "period": "1y"
		
		For stock_symbol Do not use other characters or words. Just the stock
		symbol. Do not use points, commas, or any other characters. Just the stock
		symbol and dash if it is needed.
		
		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		"""
)

historical_data_chain = (
		historical_data_template | base_llm_vertexai | output_parser
)


@tool
def get_historical_trends_and_price_data(
		stock_symbol: str,
		period: Literal[
			"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
		] = "1y",
) -> str:
	"""
	Input parameters:
	- stock_symbol: str, for example "AAPL", "MSFT", "TSLA", etc.
	- period: str, period for which to get the historical trends and price data.
	for example "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd",
	"max". No other values are accepted. Default is "1y".
	"""
	stock_symbol = stock_symbol.upper()
	stock_symbol = stock_symbol.strip()
	stock_symbol = stock_symbol.replace(" ", "")
	stock_symbol = stock_symbol.replace(".", "-")
	
	period = period.lower()
	period = period.strip()
	period = period.replace(" ", "")
	
	try:
		ticker = yf.Ticker(stock_symbol)

		if period == "1d":
			df = ticker.history(period=period, interval="1h")
		elif period == "5d":
			df = ticker.history(period=period, interval="1d")
		elif period == "1mo":
			df = ticker.history(period=period, interval="1wk")
		elif period == "3mo":
			df = ticker.history(period=period, interval="1wk")
		elif period in {"6mo", "1y", "2y", "5y"}:
			df = ticker.history(period=period, interval="1mo")
		elif period in {"10y", "ytd", "max"}:
			df = ticker.history(period=period, interval="3mo")
		else:
			raise ValueError("Invalid period provided.")
		df.index.name = 'Date'
		df_reset = df.reset_index()
		df_reset['Date'] = df_reset['Date'].dt.strftime('%Y-%m-%d')
		stock_history = df_reset.to_dict(orient='records')

		df = ticker.get_dividends()
		df.index.name = 'Date'
		df_reset = df.reset_index()
		df_reset['Date'] = df_reset['Date'].dt.strftime('%Y-%m-%d')
		dividends = df_reset.to_dict(orient='records')

		df = ticker.get_splits()
		df.index.name = 'Date'
		df_reset = df.reset_index()
		df_reset['Date'] = df_reset['Date'].dt.strftime('%Y-%m-%d')
		splits = df_reset.to_dict(orient='records')

		response = {}
		if stock_history:
			response["stock_history"] = stock_history
		if dividends:
			response["dividends"] = dividends
		if splits:
			response["splits"] = splits

		if not response:
			raise ValueError("No data found for the stock symbol provided.")

		return str(response) + "SUCCESS"

	except Exception as e:
		logger.error(
			f"Error getting stock history values symbol {stock_symbol} / "
			f"period {period}: {e}"
		)
		return (
			"Sorry, I could not get stock history values "
			"for the stock symbol you provided."
		)


historical_trends_template = PromptTemplate(
	input_variables=[
		"historical_trends_and_price_data", "user_query", "history",
		"language"
	],
	template="""
		You are a helpful AI stock history value and trends analyst.
		Your job is to understand the user's query and stock history values.

		This is the user query:
		{user_query}

		This is the stock history values:
		"{historical_trends_and_price_data}"

		This is the conversation history so far:
		{history}

		Interpret for the user the stock history values and provide the
		analysis to the user. Do not make it to short or too long. Make it just
		right.

		Try to engage the user in another conversation. 

		If not part of the conversation history you can inform the user that you 
		can offer the following additional services:
		- Stock news
		- Stock financial health
		- Stock earnings and forecasting
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

historical_trends_chain = historical_trends_template | base_llm_vertexai


def historical_trends_and_price_data_node(
		state: State
) -> Command[Literal["historical_trends_and_price_data_node"]]:
	language = state.get("language", "english")
	
	messages = get_historical_and_new_msg(state=state)
	history = messages["history"]
	new_message = messages["new_message"]
	
	json_resp = historical_data_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"format_instructions": format_instructions
		}
	)
	
	if not json_resp.get("stock_symbol"):
		logger.error(
			f"Error getting stock symbol from the user message {json_resp}"
		)
		resp = translate(
			msg=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT,
			language=language
		)
	else:
		result = get_historical_trends_and_price_data.invoke(
			{
				"stock_symbol": json_resp.get("stock_symbol"),
				"period": json_resp.get("period", "1y")
			}
		)

		messages = get_historical_and_new_msg(state=state)
		user_query = messages["new_message"]
		history = messages["history"]
	
		extraction_result = historical_trends_chain.invoke(
			{
				"user_query": str(user_query),
				"historical_trends_and_price_data": result,
				"history": str(history),
				"language": language
			}
		)
		
		resp = extraction_result.content

	return Command(
		update={
			"messages": [
				AIMessage(
					content=resp,
					name="historical_trends_and_price_data_node"
				)
			]
		},
		goto=END,
	)
