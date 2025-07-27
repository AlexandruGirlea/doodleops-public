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
from llm_graph.sub_graphs.shopping.nodes.web_search import web_search_node
from llm_graph.sub_graphs.shopping.nodes.research import research_node
from llm_graph.sub_graphs.shopping.nodes.conversation import conversation_node
from llm_graph.sub_graphs.shopping.nodes.reviews import review_node
from llm_graph.nodes.image_similarity_search_node import image_search_node


shopping_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"conversation_node", "research_node", "review_node",
		"web_search_node", "image_search_node",
	],
	additional_info="""
		You, as the shopping and selling AI supervisor assistant serve as the
		primary decision-maker in the shopping selling flow.
		
		You determine the most appropriate next step. You have the following
		workers:
		
		- 'conversation_node' Route to this node if you need to gather
		more information from the user before going to the next nodes. This node
		only gathers the necessary information by interacting with the user, it
		does not research to find product options and it does not search the
		internet to suggest where to buy or sell a product.
		This node can also help by formulating ads for the user if he needs to
		sell a product. Switch to the next nodes if the user provides enough
		information or seems to be running out of patience.
		
		- `research_node` Route to this node if the user does not know
		exactly what they are looking for and we need to research online for
		options or ideas to help the user. This node will respond to the user with
		a list of options, ideas, recommendations or product analysis, reviews,
		or specifications. Also route to this node if the user is unhappy with the
		conversation so far and you determine that further research is needed.
		But if the shopping needs change and additional information is needed
		route to `conversation_node`. Do not route to this node if the user
		is looking for product reviews. For product reviews go to `review_node`.
		
		- `web_search_node` Route to this node if the user knows
		what they are looking for and they need to find a place to buy or sell it.
		This node will do a google search and respond with a list of URL links
		where the user can buy or sell the product.
		
		- `review_node` Route to this node if the user wants reviews on a product
		he is interested in buying. This node will search the internet for both
		written and video reviews and will respond with a summary of the reviews
		and a list of links where the user can read of see video reviews.
		For product reviews always go to this node.
		
		- `image_search_node` Route to this node only if the user says he wants to
		buy or sell a product similar to a product in an image and has provided
		the image media file url link. This node will search for similar images to
		the one the user provides returns a list of websites where the similar
		images were found. Do not route to this node if the user did not yet
		provide the image media file url link, in that case route to the
		`conversation_node` to ask for it.
		
		VERY IMPORTANT: DO NOT help the user search for illegal products or 
		services, go to `conversation_node` node if the user asks for
		such products to try to steer the conversation in the right direction.
		"""
)

shopping_builder = StateGraph(State)
shopping_builder.add_node("shopping_supervisor_node", shopping_supervisor_node)
shopping_builder.add_node("conversation_node", conversation_node)
shopping_builder.add_node("research_node", research_node)
shopping_builder.add_node("web_search_node", web_search_node)
shopping_builder.add_node("review_node", review_node)
shopping_builder.add_node("image_search_node", image_search_node)

shopping_builder.add_edge(START, "shopping_supervisor_node")
shopping_graph = shopping_builder.compile()


if settings.ENV_MODE == "local":
	shopping_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "shopping_graph.png"
		)
	)


def call_shopping_graph(state: State) -> Command[Literal["shopping_graph"]]:
	response = shopping_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"language": state.get("language"),
			"all_llm_costs": state.get("all_llm_costs"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					name="shopping_graph",
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
				)
			],
		},
		goto=END,
	)
