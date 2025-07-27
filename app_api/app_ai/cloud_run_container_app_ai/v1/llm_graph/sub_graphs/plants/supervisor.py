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
from llm_graph.sub_graphs.plants.nodes.conversation import conversation_node
from llm_graph.sub_graphs.plants.nodes.media import media_node
from llm_graph.sub_graphs.plants.nodes.research import research_node


plant_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=["conversation_node", "media_node", "research_node"],
	additional_info="""
		You, as the plants advice supervisor AI assistant, serve as the primary
		decision-maker in the plants advice flow.
		You determine the most appropriate next step. You have the following
		workers:
		
		- 'conversation_node': Route all conversations to this node when they do
		not clearly match the criteria for any other specialized node. This node
		acts as the central funnel to engage the user, clarify ambiguous requests,
		and gather any missing details—whether it is information about what
		to research, or the required media link to process an image. It’s used
		whenever the necessary information is incomplete or unclear, ensuring the
		user’s intent is properly understood before proceeding.
		
		- 'media_node': Route here only if the user provides a image media file
		URL link in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found. This node will process the image, it can identify
		the plant and provide information about it, how to take care of it,
		etc. but only if the user provided a media link to the image, if not
		route to the `conversation_node` to ask for it.
		
		- 'research_node': Route to this node if you need to
		to research online for plants-related information like how to take
		care of a plant, what plant to buy, where to buy a plant, etc. This node
		does not process any media files. This node can provide advice, answers,
		help or research on plants-related needs but is able only to process
		textual information, no media files
		
		VERY IMPORTANT: DO NOT provide or facilitate advice that involves 
		unethical, illegal, or unlicensed professional services, for example:
		how to process plants to extract illegal substances.
		If such requests arise, steer the conversation back to gathering
		appropriate plant-related details by routing to `conversation_node`.
		"""
)

plant_advice_builder = StateGraph(State)
plant_advice_builder.add_node("plant_supervisor_node", plant_supervisor_node)
plant_advice_builder.add_node("conversation_node", conversation_node)
plant_advice_builder.add_node("media_node", media_node)
plant_advice_builder.add_node("research_node", research_node)

plant_advice_builder.add_edge(START, "plant_supervisor_node")
plant_graph = plant_advice_builder.compile()

if settings.ENV_MODE == "local":
	plant_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "plant_advice_graph.png"
		)
	)


def call_plant_graph(
		state: State
) -> Command[Literal["plant_graph"]]:
	response = plant_graph.invoke(
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
					name="plant_graph"
				)
			],
		},
		goto=END,
	)
