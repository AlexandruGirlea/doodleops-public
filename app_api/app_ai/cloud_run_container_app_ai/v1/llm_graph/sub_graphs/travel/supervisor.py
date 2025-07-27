import os
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START

from core import settings
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.conversations_state import State
from llm_graph.utils.build_supervisor_nodes import make_supervisor_node
from llm_graph.sub_graphs.travel.nodes.media import media_node
from llm_graph.sub_graphs.travel.nodes.research import research_node
from llm_graph.sub_graphs.travel.nodes.web_search import web_search_node
from llm_graph.sub_graphs.travel.nodes.conversation import conversation_node

travel_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"conversation_node", "media_node", "research_node", "web_search_node"
	],
	additional_info="""
		You are the AI travel agent, serving as the primary decision-maker.
		
		You determine the most appropriate next step. You have the following
		workers:
		
		`conversation_node`: Route all conversations to this node when they do
		not clearly match the criteria for any other specialized node. This node
		acts as the central funnel to engage the user, clarify ambiguous requests,
		and gather any missing details. This node is offline and cannot
		process media files or do online research.
		
		`media_node`: Route here only if the user provides a media file URL
		link (e.g., image or PDF) in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found. This node can interpret images or read pdf documents to provide
		the user with solutions. For example: the user uploads a picture of a
		place he would like to visit, the node can identify the place and provide
		information about it. Do not route to this node if the user did not
		provide the media file url link, for that route to the
		`conversation_node` to ask for it.
		
		`research_node`: Route to this node if you determine that the best
		course of action is to do some research online to find the information
		the user needs. This node can provide source citations but cannot process
		media files url links.
		
		`web_search_node`: Route to this node if you determine that the best
		course of action is to do a google search.
		This node will respond to the user with different
		travel related website links. This is different from the
		research node. It does not do research, call this node only when it's
		clear what the user needs to search for.
"""
)
travel_builder = StateGraph(State)
travel_builder.add_node("travel_supervisor_node", travel_supervisor_node)
travel_builder.add_node("conversation_node", conversation_node)
travel_builder.add_node("media_node", media_node)
travel_builder.add_node("research_node", research_node)
travel_builder.add_node("web_search_node", web_search_node)

travel_builder.add_edge(START, "travel_supervisor_node")
travel_graph = travel_builder.compile()

if settings.ENV_MODE == "local":
	travel_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "travel_graph.png"
		)
	)


def call_travel_graph(
		state: State
) -> Command[Literal["travel_graph"]]:
	response = travel_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"language": state.get("language", "english"),
			"all_llm_costs": state.get("all_llm_costs"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					name="travel_graph",
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
				)
			],
		},
		goto=END,
	)
