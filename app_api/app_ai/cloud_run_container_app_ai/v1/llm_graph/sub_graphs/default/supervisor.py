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
from llm_graph.sub_graphs.default.nodes.research import research_node
from llm_graph.sub_graphs.default.nodes.conversation import conversation_node
from llm_graph.sub_graphs.default.nodes.our_services import our_services_node
from llm_graph.sub_graphs.default.nodes.media import media_node
from llm_graph.nodes.search_youtube_video import search_youtube_video_node
from llm_graph.sub_graphs.default.nodes.unknown_prompt import unknown_prompt_node


default_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai, members=[
		"conversation_node", "research_node", "our_services_node",
		"media_node", "search_youtube_video_node", "unknown_prompt_node"
	],
	additional_info="""
		You are a General AI assistant. You are here to help the user.
		
		You determine the most appropriate next step. You have the following
		workers:
		- `conversation_node`: Route to this node to have a conversation
		with the user. This conversation does not need to be about solving a
		problem for the user, it can just be a friendly conversation about
		life, the universe, and everything. Also route to this node
		if you need addition information from the user for other nodes.
		This an offline node with no access to the internet.
		
		- `our_services_node`: Route to this node to inform the user about the
		services you offer. This an offline node with no access to the internet.
		
		- `research_node`: Route to this node to search the internet
		or to do research for the user. Use this node if form the conversation
		context, you need to search the internet for more information.
		This node scans the entire internet for information, not only text but
		also videos, and can return a more comprehensive answer to the user.
		If the user prefers answers that have video links, do not use this node,
		instead use the `search_youtube_video_node`.
		
		- `media_node`: Route here only if the user provides a media file URL
		link (e.g., image or PDF) in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found. This is the only node that can process media files. Do not
		route here if the user intends to process a media file but did not provide
		a link, in that case route to the `conversation_node` to ask for it.
		
		- `search_youtube_video_node`: Route to this node if you think that
		the user needs might benefit from seeing a youtube video on the topic.
		This node can provide youtube video links on different types of
		products and services like: comparison, reviews, unboxing, long term
		use, diy, etc. Think of this node like a very powerful web search that
		only returns youtube video links on the topic the user needs help with.
		
		- `unknown_prompt_node`: Route to this node If the user prompt does not
		make any sense, or the user is rude. Do not be extra sensitive and
		route to this node if the user is just trying to be funny or
		lighthearted. For example if the user asks for a joke or something
		silly. In that case route to the `conversation_node` instead.
		"""
)

default_builder = StateGraph(State)
default_builder.add_node("default_supervisor_node", default_supervisor_node)
default_builder.add_node("conversation_node", conversation_node)
default_builder.add_node("our_services_node", our_services_node)
default_builder.add_node("research_node", research_node)
default_builder.add_node("media_node", media_node)
default_builder.add_node("search_youtube_video_node", search_youtube_video_node)
default_builder.add_node("unknown_prompt_node", unknown_prompt_node)

default_builder.add_edge(START, "default_supervisor_node")
default_graph = default_builder.compile()

if settings.ENV_MODE == "local":
	default_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "default_graph.png"
		)
	)


def call_default_graph(state: State) -> Command[Literal["default_graph"]]:
	response = default_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"all_llm_costs": state.get("all_llm_costs"),
			"language": state.get("language"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
					name="default_graph"
				)
			]
		},
		goto=END,
	)
