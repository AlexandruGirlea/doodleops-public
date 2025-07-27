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
from llm_graph.sub_graphs.video_generator.nodes.conversation import (
	conversation_node,
)
from llm_graph.sub_graphs.video_generator.nodes.text_to_video import (
	text_to_video_node
)
from llm_graph.sub_graphs.video_generator.nodes.image_to_video import (
	image_to_video_node
)


video_generator_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=["conversation_node", "text_to_video_node", "image_to_video_node"],
	additional_info="""
		You, as the video generator supervisor assistant, serve as the primary
		decision-maker in the video generation process.
		You determine the most appropriate next step to generate the best
		video for the user based on the conversation so far. You evaluate if
		you have a good enough information to generate an excellent video.
		For example: if it's a text to video request, you might need details how
		the video should look like, what it should contain, etc.
		If it's a image to video request, you might need to know how the user
		wants to animate that image.
		
		If the user is running out of patience you should decide between the two
		options: `text_to_video_node` or `image_to_video_node`.
		
		If the user is unhappy with the previous video or wants to try again, you
		can route to the `conversation_node` worker to gather more information.
		
		If you need to gather more information from the user call the
		`conversation_node` worker.
		
		Your workers are:
		
		- `conversation_node`: This worker is responsible for gathering
		information from the user about the video or design they want to
		generate. Route to this node when the conversation has just started or
		when it's still somewhat unclear what video should look like or what it
		should contain.
		
		- `text_to_video_node`: This worker is responsible for generating a new
		video based on the user's request. This is a text prompt to video
		generation model. Route to this worker when it's
		clear what video the user wants to generate or route here if the video
		conversation has been going on for a while and the user has not provided
		enough information. Also Route to this worker if the user was not happy
		with the previous video or wants you to try again.
		
		- `image_to_video_node`: This worker is responsible for generating a new
		video based on the user's provided image. Route to this worker when the
		user has provided an image and wants to generate a video based on it.
		For example the user might say "generate a video based on this image"
		or "make them come alive" or "animate this image" and so on.
		

		Attention: if what the user is asking for might be inappropriate, 
		offensive or illegal or the prompt might suggest
		that the user wants a video that might include children or teenagers,
		route to `conversation_node` so that we can steer the conversation in the
		right direction.
		"""
)

video_generator_builder = StateGraph(State)
video_generator_builder.add_node(
	"video_generator_supervisor_node", video_generator_supervisor_node
)
video_generator_builder.add_node("conversation_node", conversation_node)
video_generator_builder.add_node("text_to_video_node", text_to_video_node)
video_generator_builder.add_node("image_to_video_node", image_to_video_node)

video_generator_builder.add_edge(START, "video_generator_supervisor_node")
video_generator_graph = video_generator_builder.compile()

if settings.ENV_MODE == "local":
	video_generator_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "video_generator_graph.png"
		)
	)


def call_video_generator_graph(
		state: State
) -> Command[Literal["video_generator_graph"]]:

	response = video_generator_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"language": state.get("language", "english"),
			"username": state.get("username"),
			"all_llm_costs": state.get("all_llm_costs"),
			"user_total_available_credits": state.get(
				"user_total_available_credits"),
			"has_metered_subscription": state.get("has_metered_subscription"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
					name="video_generator_graph"
				)
			],
		},
		goto=END,
	)
