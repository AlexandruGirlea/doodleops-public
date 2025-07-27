import os
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langgraph.graph import StateGraph, START
from langchain_core.messages import AIMessage

from core import settings
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.conversations_state import State
from llm_graph.utils.build_supervisor_nodes import make_supervisor_node
from llm_graph.sub_graphs.stocks.nodes.conversation import conversation_node
from llm_graph.sub_graphs.stocks.nodes.earnings_and_forecasting import (
	earnings_and_forecasting_node,
)
from llm_graph.sub_graphs.stocks.nodes.financial_health import (
	financial_health_node
)
from llm_graph.sub_graphs.stocks.nodes.general_info import general_info_node
from llm_graph.sub_graphs.stocks.nodes.historical_trends_and_price_data import (
	historical_trends_and_price_data_node,
)
from llm_graph.sub_graphs.stocks.nodes.market_sentiment import (
	market_sentiment_node
)
from llm_graph.sub_graphs.stocks.nodes.news import news_node
from llm_graph.sub_graphs.stocks.nodes.research import research_node
from llm_graph.sub_graphs.stocks.nodes.in_depth_stock_analysis import (
	in_depth_stock_analysis_node,
)


stock_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"conversation_node", "earnings_and_forecasting_node",
		"financial_health_node", "general_info_node",
		"historical_trends_and_price_data_node",
		"market_sentiment_node", "news_node",
		"research_node", "in_depth_stock_analysis_node",
	],
	additional_info="""
		You, as the stock supervisor assistant serve as the primary 
		decision-maker in the stock information flow.
		You determine the most appropriate next step. You have the following 
		workers:
		- 'conversation_node' which is a node that helps talk to the user
		and gather information about what they are looking to know about one or
		more stocks. It's job is to is to gather information about what the user 
		needs. This is also a fallback AI stock assistant that helps the user.
		Route to this node if you need more information before going to the
		other nodes. If the user seems to not know what other information you can 
		provide also rout the conversation to this node. It will help him.
		This node tells the user about all the stock services you can provide.
		
		- 'general_info_node' which is a node that helps get general
		information about one or more stocks. It needs the Stock symbol or symbols
		to get the information.  ONLY for US stocks.
		Route to this node if you need general information about one or more 
		stocks. Do not route to this node if user asks for information
		about your capabilities. Route to `conversation_node` instead.
		
		- 'earnings_and_forecasting_node' which is a node that helps
		get information about the earnings and forecasting of ONE specific stock.
		Route to this node if you need information about the earnings and
		forecasting of ONE specific stock. ONLY for US stocks.
		
		- 'financial_health_node' which is a node that helps get
		information about the financial health of ONE specific stock.
		Route to this node if you need information about the financial health
		of ONE specific stock. ONLY for US stocks.
		
		- 'historical_trends_and_price_data_node' which is a node that
		helps get information about the historical trends and price data of
		ONE specific stock.
		Route to this node if you need information about the historical trends
		and price data of ONE specific stock. ONLY for US stocks.
		
		- 'market_sentiment_node' which is a node that helps get
		information about the market sentiment of ONE specific stock.
		Route to this node if you need information about the market sentiment	
		of ONE specific stock. ONLY for US stocks.
		
		- 'news_node' which is a node that you should call only if the user
		asks about latest NEWS about ONE specific stock.
		Route to this node if you need news about one particular stock.
		If in the conversation history we already provided news about this stock
		then route to `research_node` because it can search the internet
		for additional information. ONLY for US stocks.
		
		- `in_depth_stock_analysis_node` which is a node that helps get in depth
		analysis of a stock. Allways call this node if the user wants more
		in depth analysis of a stock. This node will call all the other nodes
		to get the information. Only call this node if the user asks for analysis
		on one single specific stock. FOR ALL STOCKS in the world.
		
		- 'research_node' this node helps the user by searching the
		internet for the hottest general information about a stock like:
		best stocks to buy, best stocks to sell, etc. or what is currently
		happening in the stock market. Route to this node only if other nodes do
		not fit the user query. ONLY for US stocks.
		"""
)

stock_builder = StateGraph(State)
stock_builder.add_node("stock_supervisor_node", stock_supervisor_node)
stock_builder.add_node("conversation_node", conversation_node)
stock_builder.add_node(
	"earnings_and_forecasting_node", earnings_and_forecasting_node
)
stock_builder.add_node("financial_health_node", financial_health_node)
stock_builder.add_node("general_info_node", general_info_node)
stock_builder.add_node(
	"historical_trends_and_price_data_node", historical_trends_and_price_data_node
)
stock_builder.add_node("market_sentiment_node", market_sentiment_node)
stock_builder.add_node("news_node", news_node)
stock_builder.add_node("research_node", research_node)
stock_builder.add_node(
	"in_depth_stock_analysis_node", in_depth_stock_analysis_node
)


stock_builder.add_edge(START, "stock_supervisor_node")
stock_graph = stock_builder.compile()

if settings.ENV_MODE == "local":
	stock_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "stock_graph.png"
		)
	)


def call_stock_graph(state: State) -> Command[Literal["stock_graph"]]:
	response = stock_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"all_llm_costs": state.get("all_llm_costs"),
			"language": state.get("language", "english"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					name="stock_graph",
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
				)
			],
		},
		goto=END,
	)
