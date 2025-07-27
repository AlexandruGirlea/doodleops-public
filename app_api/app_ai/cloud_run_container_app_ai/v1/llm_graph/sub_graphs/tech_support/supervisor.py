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
from llm_graph.sub_graphs.tech_support.nodes.media import media_node
from llm_graph.sub_graphs.tech_support.nodes.research import research_node
from llm_graph.nodes.search_youtube_video import search_youtube_video_node
from llm_graph.sub_graphs.tech_support.nodes.conversation import conversation_node

tech_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"conversation_node", "media_node", "research_node",
		"search_youtube_video_node"
	],
	additional_info="""
		You are the AI tech supervisor, serving as the primary decision-maker.
		
		You determine the most appropriate next step. You have the following
		workers:
		
		- `conversation_node`: Route all conversations to this node when they do
		not clearly match the criteria for any other specialized node. This node
		acts as the central funnel to engage the user, clarify ambiguous requests,
		and gather any missing details. This node can also be used to
		provide step-by-step guidance or answer questions that a tech person would
		know. It is offline and cannot process media files or do online research
		for the more complicated or specific inquiries. Route to this node
		to try to answer code-related questions, provide general tech advice,
		or help with tech-related issues.
		
		- `media_node`:  Route here only if the user provides a media file URL
		link (e.g., image or PDF) in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found. This node can interpret media files to provide the user with the
		possible issues or fix suggestions.
		
		- `search_youtube_video_node`: Route to this node if you consider that the
		best way to help the user is to provide video instructions or tutorials.
		This node understands the conversation context and searches youtube and
		returns the most relevant video for the user's request. Try to not route
		to this node if the user needs help with coding something, this is more
		useful for stuff like: how to deactivate face tracking on a phone, etc.
		Attention: only route to this node if the user is speaking in English.
		If the user is not speaking in English, but still
		needs some indepth instructions, route to the `research_node`.
		
		- `research_node`: Route to this node when in order to help the user
		you need to do some research online or need more specific
		information. This node can provide source citations but cannot process
		media files. This node can also help with coding problems that require
		more up-to-date information or specific examples, because it can search
		the web.
"""
)

tech_builder = StateGraph(State)
tech_builder.add_node("tech_supervisor_node", tech_supervisor_node)
tech_builder.add_node("conversation_node", conversation_node)
tech_builder.add_node("media_node", media_node)
tech_builder.add_node("search_youtube_video_node", search_youtube_video_node)
tech_builder.add_node("research_node", research_node)

tech_builder.add_edge(START, "tech_supervisor_node")
tech_graph = tech_builder.compile()

if settings.ENV_MODE == "local":
	tech_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "tech_graph.png"
		)
	)


def call_tech_graph(
		state: State
) -> Command[Literal["tech_graph"]]:
	response = tech_graph.invoke(
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
					name="tech_graph"
				)
			],
		},
		goto=END,
	)
