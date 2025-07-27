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
from llm_graph.sub_graphs.handyman.nodes.media import media_node
from llm_graph.sub_graphs.handyman.nodes.research import research_node
from llm_graph.sub_graphs.handyman.nodes.conversation import conversation_node

handyman_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=["conversation_node", "media_node", "research_node"],
	additional_info="""
		You are the AI Handyman supervisor, serving as the primary decision-maker.
		
		You determine the most appropriate next step. You have the following
		workers:
		
		`conversation_node`: Route all conversations to this node when they do
		not clearly match the criteria for any other specialized node. This node
		acts as the central funnel to engage the user, clarify ambiguous requests,
		and gather any missing details. This node can also be used to
		provide step-by-step guidance or answer questions that a handyman would
		know. It is offline and cannot process media files or do online research
		for the more complicated or specific inquiries.
		
		`media_node`: Route here only if the user provides a media file URL
		link (e.g., image or PDF) in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found. This node can interpret images or read pdf documents to provide
		the user with the possible issues or fix suggestions. Rout to this not
		only if the url link was provided, else route to the `conversation_node`
		who will ask for it.
		
		`research_node`: Route to this node when in order to help the user
		you need to do some research online or need more specific
		information. This node can provide source citations but cannot process
		media files.
"""
)

handyman_builder = StateGraph(State)
handyman_builder.add_node("handyman_supervisor_node", handyman_supervisor_node)
handyman_builder.add_node("conversation_node", conversation_node)
handyman_builder.add_node("media_node", media_node)
handyman_builder.add_node("research_node", research_node)

handyman_builder.add_edge(START, "handyman_supervisor_node")
handyman_graph = handyman_builder.compile()

if settings.ENV_MODE == "local":
	handyman_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "handyman_graph.png"
		)
	)


def call_handyman_graph(
		state: State
) -> Command[Literal["handyman_graph"]]:
	response = handyman_graph.invoke(
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
					name="handyman_graph"
				)
			],
		},
		goto=END,
	)
