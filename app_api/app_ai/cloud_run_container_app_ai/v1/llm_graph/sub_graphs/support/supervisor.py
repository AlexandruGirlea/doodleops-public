import os
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START

from core import settings
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.build_supervisor_nodes import make_supervisor_node
from llm_graph.sub_graphs.support.nodes.support import support_node
from llm_graph.sub_graphs.support.nodes.suggest_new_feature import (
	suggest_new_feature_node,
)
from llm_graph.sub_graphs.support.nodes.feedback import feedback_node
from llm_graph.sub_graphs.support.nodes.support_conversation import (
	support_conversation_node,
)


support_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai, members=[
		"feedback_node", "support_node", "suggest_new_feature_node",
		"support_conversation_node",
	],
	additional_info="""
		You are an AI assistant router. You are here to help the user by routing
		him to the correct node based on his needs.
		
		You determine the most appropriate next step. You have the following
		workers:
		- `support_conversation_node`:  Route to this node if the user does not
		know what kind of help he needs or the prompt does not fit any other
		category.
		- `feedback_node`: The user wants to provide feedback on a feature or
		wants to register a bug report.
		- `support_node`: The user wants to create a support ticket, he needs help
		with a tool that we offer or he thinks the tool is not working as 
		expected.
		- `suggest_new_feature_node`: The user wants to suggest a new feature or 
		the current feature is not working as expected.
		
		When in doubt, route to `support_conversation_node`.
		"""
)

support_builder = StateGraph(State)
support_builder.add_node("support_supervisor_node", support_supervisor_node)
support_builder.add_node("support_conversation_node", support_conversation_node)
support_builder.add_node("feedback_node", feedback_node)
support_builder.add_node("support_node", support_node)
support_builder.add_node("suggest_new_feature_node", suggest_new_feature_node)

support_builder.add_edge(START, "support_supervisor_node")
support_graph = support_builder.compile()

if settings.ENV_MODE == "local":
	support_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "support_graph.png"
		)
	)


def call_support_graph(state: State) -> Command[Literal["support_graph"]]:
	response = support_graph.invoke(
		{
			"messages": state["messages"],
			"user_phone_number": state.get("user_phone_number"),
			"all_llm_costs": state.get("all_llm_costs"),
			"language": state.get("language", "english"),
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
					name="support_graph"
				)
			]
		},
		goto=END,
	)
