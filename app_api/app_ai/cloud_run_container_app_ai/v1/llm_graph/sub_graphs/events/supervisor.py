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
from llm_graph.sub_graphs.events.nodes.research import research_node
from llm_graph.sub_graphs.events.nodes.web_search import web_search_node
from llm_graph.sub_graphs.events.nodes.conversation import conversation_node

events_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"conversation_node", "research_node", "web_search_node"
	],
	additional_info="""
		You are the AI Events agent, serving as the primary decision-maker.
		You determine the most appropriate next step to help users with their
		events-related requests. You have three specialized nodes available:
		
		`conversation_node`: Rout to this node to clarify or gather more
		information about the user’s events needs. This node is offline and cannot
		do online research.
		
		`research_node`: Route to this node if you determine that the best
		course of action is to do some research online to find the information
		the user needs. This node can provide source citations. This node is best
		suited for more complex requests like, getting information about an
		event or how to plan an event, etc.
		
		`web_search_node`: Route to this node if you determine that the best
		course of action is to do a google search.
		This node will respond to the user with different
		events related url links from google. This is different from the
		research node. It does not do research or is capable to have a
		conversation with the user, it only returns URL Links. Call this node
		only when it's clear what the user needs to search for.
	"""
	)


events_builder = StateGraph(State)
events_builder.add_node("events_supervisor_node", events_supervisor_node)
events_builder.add_node("conversation_node", conversation_node)
events_builder.add_node("research_node", research_node)
events_builder.add_node("web_search_node", web_search_node)

events_builder.add_edge(START, "events_supervisor_node")
events_graph = events_builder.compile()

if settings.ENV_MODE == "local":
	events_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "events_graph.png"
		)
	)


def call_events_graph(
		state: State
) -> Command[Literal["events_graph"]]:
	response = events_graph.invoke(
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
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
					name="events_graph"
				)
			],
		},
		goto=END,
	)
