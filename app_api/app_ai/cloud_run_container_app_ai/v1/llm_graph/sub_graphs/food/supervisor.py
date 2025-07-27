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
from llm_graph.sub_graphs.food.nodes.media import media_node
from llm_graph.sub_graphs.food.nodes.research import research_node
from llm_graph.sub_graphs.food.nodes.conversation import conversation_node

food_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=["conversation_node", "media_node", "research_node"],
	additional_info="""
		You are the AI Food supervisor, serving as the primary decision-maker.
		You determine the most appropriate next step to help users with their
		food-related requests. You have three specialized nodes available:
		
		`conversation_node`: Rout to this node to clarify or gather more
		information about the user’s request. This node can also be used to
		provide step-by-step guidance or answer questions that a cook would
		know. It is offline and cannot process media files or do online research
		for the more complicated or specific inquiries.
		
		`media_node`:  Route here only if the user provides a media file URL
		link (e.g., image or PDF) in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found. This node can interpret images or read pdf documents to provide
		the user with solutions. For example: the user uploads a picture of
		ingredients and and needs some suggestions on what to cook.
		
		`research_node`: Route to this node in order to help the user
		do some research online or he needs more specific information. This node 
		can provide source citations but cannot process media files.
"""
)

food_builder = StateGraph(State)
food_builder.add_node("food_supervisor_node", food_supervisor_node)
food_builder.add_node("conversation_node", conversation_node)
food_builder.add_node("media_node", media_node)
food_builder.add_node("research_node", research_node)

food_builder.add_edge(START, "food_supervisor_node")
food_graph = food_builder.compile()

if settings.ENV_MODE == "local":
	food_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "food_graph.png"
		)
	)


def call_food_graph(
		state: State
) -> Command[Literal["food_graph"]]:
	response = food_graph.invoke(
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
					name="food_graph"
				)
			],
		},
		goto=END,
	)
