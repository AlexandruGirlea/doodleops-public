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
from llm_graph.sub_graphs.image_generator.nodes.conversation import (
	conversation_node,
)
from llm_graph.sub_graphs.image_generator.nodes.image_generator import (
	image_generator_node
)


image_generator_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=["conversation_node", "image_generator_node"],
	additional_info="""
		You, as the image generator supervisor assistant, serve as the primary
		decision-maker in the image generation process.
		You determine the most appropriate next step to generate the best
		image for the user based on the conversation so far. You evaluate if
		you have a good enough information to generate an excellent image using
		the `image_generator_node` worker. If you need to gather more information
		from the user call the `conversation_node` worker.
		
		Your workers are:
		
		- `conversation_node`: This worker is responsible for gathering
		information from the user about the image or design they want to
		generate. Route to this node when the conversation has just started or
		when it's still somewhat unclear what image or design should look like.
		
		- `image_generator_node`: This worker is responsible for generating the
		image / design based on the user's request. Route to this worker when it's
		clear what image the user wants to generate or route here if the image
		conversation has been going on for a while and the user has not provided
		enough information. Also Route to this worker if the user was not happy
		with the previous image or wants you to try again.
		This worker is also capable to generate designs for logos, banners,
		flyers, social media posts, and other visual content. But it needs the
		appropriate information in the context which the
		`conversation_node` worker can get.
		
		Attention: if what the user is asking for might be inappropriate, 
		offensive or illegal or the prompt might suggest
		that the user wants an image that might include children or teenagers,
		route to `conversation_node` so that we can steer the conversation in the
		right direction.
		"""
)

image_generator_builder = StateGraph(State)
image_generator_builder.add_node(
	"image_generator_supervisor_node", image_generator_supervisor_node
)
image_generator_builder.add_node("conversation_node", conversation_node)
image_generator_builder.add_node("image_generator_node", image_generator_node)

image_generator_builder.add_edge(START, "image_generator_supervisor_node")
image_generator_graph = image_generator_builder.compile()

if settings.ENV_MODE == "local":
	image_generator_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "image_generator_graph.png"
		)
	)


def call_image_generator_graph(
		state: State
) -> Command[Literal["image_generator_graph"]]:
	response = image_generator_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"language": state.get("language", "english"),
			"username": state.get("username"),
			"all_llm_costs": state.get("all_llm_costs"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
					name="image_generator_graph"
				)
			],
		},
		goto=END,
	)
