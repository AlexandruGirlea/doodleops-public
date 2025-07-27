import json
import logging
from typing import Literal

import yfinance as yf
from langgraph.graph import END
from langgraph.types import Command
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, SystemMessage

from llm_graph.utils.conversations_state import State
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.llm_models import lite_llm_vertexai, base_llm_vertexai


logger = logging.getLogger("APP_AI_V1_" + __name__)


@tool
def get_general_info_one_stock(stock_symbol: str, ) -> str:
	"""
	Get one general information for a given stock symbol.
	Provide the stock symbol as the input to this tool.
	Example: "AAPL" or "BRK-B"
	
	Do not use other characters or words, just the stock symbol. Do not use
	points, or any other characters. Just the stock symbol and dash
	if it is necessary.
	"""
	stock_symbol = stock_symbol.upper()
	stock_symbol = stock_symbol.replace(" ", "")
	stock_symbol = stock_symbol.strip()
	stock_symbol = stock_symbol.replace(".", "-")
	
	try:
		ticker = yf.Ticker(stock_symbol)

		return str(
			{
				"info": json.dumps(ticker.get_info())
			}
		) + "SUCCESS"

	except Exception as e:
		logger.error(
			f"Error getting general info for stock symbol {stock_symbol}: {e}"
		)
		return (
			"Sorry, I could not find any general info "
			"for the stock symbol you provided."
		)


@tool
def get_general_info_multiple_stocks(stock_symbols: str, ) -> str:
	"""
	Get general information for multiple stock symbols separated by a comma.
	Provide the stock symbol as the input to this tool.
	
	Example: "AAPL,MSFT,TSLA,BRK-B"
	"""
	stock_symbols_clean = []
	for s in stock_symbols.split(","):
		stock_symbol = s.upper()
		stock_symbol = stock_symbol.replace(" ", "")
		stock_symbol = stock_symbol.strip()
		stock_symbol = stock_symbol.replace(".", "-")
		stock_symbols_clean.append(stock_symbol)

	clean_data = []
	try:
		for s in stock_symbols_clean:
			ticker = yf.Ticker(s)
			clean_data.append([{k: v} for k, v in ticker.fast_info.items() if v])

		return str(clean_data) + "SUCCESS"

	except Exception as e:
		if clean_data:
			return str(clean_data) + "SUCCESS"

		logger.error(
			"Error getting general info for stock symbols "
			f"{stock_symbols_clean}: {e}"
		)
		return (
			"Sorry, I could not find any general info "
			"for the stock symbols you provided."
		)


get_general_info_agent = create_react_agent(
	model=lite_llm_vertexai,
	tools=[get_general_info_one_stock, get_general_info_multiple_stocks]
)

general_info_template = PromptTemplate(
	input_variables=["general_info", "user_query", "history", "language"],
	template="""
		You are a helpful AI stock general information analyst.
		Your job is to understand the user's query and the general
		information for the stock symbol.

		This is the user query:
		{user_query}

		This is the general information:
		"{general_info}"

		This is the conversation history so far:
		{history}

		Interpret for the user the general information and provide
		it to the user. Do not make it to short or too long. Make it just right.

		Do not be very technical. Make it easy to understand for the user. Be
		technical only if the user asks for it.

		Try to engage the user in another conversation. 

		If not part of the conversation history you can inform the user that you 
		can offer the following additional services:
		- Stock news
		- Stock earnings and forecasting
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

general_info_chain = general_info_template | base_llm_vertexai


def general_info_node(state: State) -> Command[Literal["general_info_node"]]:
	language = state.get("language", "english")

	state["messages"] = [
			SystemMessage(
				content=f"""
			You are a helpful AI stock general information assistant. 

			Your job is identify the stock symbol or symbols for which the user 
			needs general information and call one of the following tools to get
			the latest general information for that stock symbol or symbols:
			- `get_general_info_one_stock` for one stock symbol
			- `get_general_info_multiple_stocks` for multiple stock symbols 
			separated by a comma.
			
			ONLY for US stocks. If the user wants information about a non-US stock
			politely inform the user that you can only provide this type of
			information for US stocks.
			
			You must respond with the exact output of the tool you called.
			""")
			] + state["messages"]

	result = get_general_info_agent.invoke(
		{"messages": state["messages"]}
	)

	messages = get_historical_and_new_msg(state=state)
	user_query = messages["new_message"]
	history = messages["history"]

	extraction_result = general_info_chain.invoke(
		{
			"user_query": str(user_query),
			"general_info": result["messages"][-1].content,
			"history": str(history),
			"language": language,
		}
	)

	return Command(
		update={
			"messages": [
				AIMessage(
					name="general_info_node",
					content=extraction_result.content,
				)
			]
		},
		goto=END,
	)
