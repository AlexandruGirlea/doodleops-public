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
from llm_graph.sub_graphs.learn.nodes.media import media_node
from llm_graph.sub_graphs.learn.nodes.research import research_node
from llm_graph.sub_graphs.learn.nodes.conversation import conversation_node

learn_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=["conversation_node", "media_node", "research_node"],
	additional_info="""
		You, as the AI Teacher supervisor, serve as the primary decision-maker.
		
		You determine the most appropriate next step. You have the following
		workers:
		
		**`conversation_node`**
		- **When to Route**: Default node for queries that do not involve media
		files or require online research. Use this for general educational tasks
		(e.g., unit conversions, homework help, math problems, geography
		questions) when the user provides the question text and no media link is
		present. Also route here to clarify ambiguous requests or gather missing
		details (e.g., if the user intends to provide a media link but hasn’t).
		- **Capabilities**: Acts as a learning assistant, guiding and teaching the
		user, using an offline AI model with broad topic coverage.
		- **Limitations**: Cannot process media files (e.g., images, PDFs) or
		answer history questions. Lacks internet access for up-to-date information.

		**`media_node`**
		- **When to Route**: Route here only if the user provides a media file URL
		link (e.g., image or PDF) in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found.
		- **Capabilities**: Processes media files and provides answers based on
		their content.
		- **Limitations**: Cannot handle queries without a media link. If the user
		mentions a media file without providing a link (e.g., "I have a photo"),
		route to `conversation_node` to request it.

		**`research_node`**
		- **When to Route**: Route here for history-related questions or any query
		requiring up-to-date information from the web (e.g., current events,
		recent data).
		- **Capabilities**: Conducts online research and provides responses with
		source citations.
		- **Limitations**: Cannot process media files.
		
		**Routing Guidelines**:
		- If a media link is provided and the query relates to it, route to
		`media_node`.
		- If the link is unrelated to the query, route to `conversation_node` to
		clarify intent.
		- For educational queries without media or a need for current data, route
		to `conversation_node`.
		- For history or web-research needs, route to `research_node`.
		- When in doubt, route to `conversation_node` to probe further.
		"""
)

learn_builder = StateGraph(State)
learn_builder.add_node("learn_supervisor_node", learn_supervisor_node)
learn_builder.add_node("conversation_node", conversation_node)
learn_builder.add_node("media_node", media_node)
learn_builder.add_node("research_node", research_node)

learn_builder.add_edge(START, "learn_supervisor_node")
learn_graph = learn_builder.compile()

if settings.ENV_MODE == "local":
	learn_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "learn_graph.png"
		)
	)


def call_learn_graph(
		state: State
) -> Command[Literal["learn_graph"]]:
	response = learn_graph.invoke(
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
					name="learn_graph"
				)
			],
		},
		goto=END,
	)
