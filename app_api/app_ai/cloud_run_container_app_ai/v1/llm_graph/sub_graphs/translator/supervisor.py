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
from llm_graph.sub_graphs.translator.nodes.conversation import conversation_node
from llm_graph.sub_graphs.translator.nodes.media import media_node
from llm_graph.sub_graphs.translator.nodes.speech_to_text import (
	speech_to_text_node
)
from llm_graph.sub_graphs.translator.nodes.text_to_speech_audio import (
	text_to_speech_audio_node
)
from llm_graph.sub_graphs.translator.nodes.text_to_text import text_to_text_node

translation_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"conversation_node", "media_node", "speech_to_text_node",
		"text_to_speech_audio_node", "text_to_text_node",
	],
	additional_info="""
		You, as the AI Translation supervisor assistant serve as the
		primary decision-maker in the translation flow.

		You determine the most appropriate next step. You have the following
		workers:

		- 'conversation_node' Route all conversations to this node when they do
		not clearly match the criteria for any other specialized node. This node
		acts as the central funnel to engage the user, clarify ambiguous requests,
		and gather any missing details—whether the input is text, image, audio, or
		another format. It’s used whenever the necessary information
		(such as the desired target language, output format, or specific media
		details) is incomplete or unclear, ensuring the user’s intent is properly
		understood before proceeding.
		
		- 'media_node' Route here only if the user provides an image media file
		URL link in the latest message or conversation history,
		and the query relates to that media. If the user hints at an uploaded file
		(e.g., "I posted a picture"), check the history for a link and route here
		if found.
		
		- 'speech_to_text_node' Route to this node only if the user has provided
		an audio file link, explicitly indicated the language of the audio file,
		and specified the target language for the translation. If any of these
		pieces of information are missing, route to ‘conversation_node’ to request
		the necessary details. When making a decision make sure to look at the
		entire conversation context and the user's intent.
		
		- 'text_to_speech_audio_node' Route to this node only if the user provided
		a text to be translated and specified the desired target language.
		This is the default text translation node.
		If any of these details are missing, route to ‘conversation_node’ to
		gather more information. When making a decision make sure to look at the
		entire conversation context and the user's intent. Also route to this node
		if the user did not clearly indicated the output format. If not instructed
		otherwise, presume the user wants the output in audio format.
		If no text was provided by the user, route to 'conversation_node' to
		gather more information.
		
		- 'text_to_text_node' Route to this node **only if** the user provided a
		text, specified the desired target language, and **explicitly requested
		that the output be in text format**. If the user does not indicate the
		output format (or the target language), route to ‘conversation_node’ to
		gather more information. When making a decision make sure to look at the
		entire conversation context and the user's intent. AGAIN, to not route to
		this node if the user did not say the translation should be in text
		format. If no format is explicitly specified, presume the user might want
		text or audio, so route to 'conversation_node' to understand.
		
		If in doubt, route to 'conversation_node' to gather more information.
		
		General rule when deciding between `text_to_text_node` and
		`text_to_speech_audio_node`: only route to them if the user explicitly
		requests the output in text or audio format respectively. If the user
		does not specify the output format, route to `conversation_node`.
		
		If the user says something like:
		"translate this to French, where is the nearest bakery?" this does not
		implicitly mean that the user wants the output in text format. The user
		just provided the text that wants to be translated and the language, you
		still need the output format, that is why you should route to
		`conversation_node`.
		
		Be aware if the user is running out of patience or the conversation
		history shows that the user is getting frustrated, you should route to
		one of the translation nodes that you think might help the user.
		"""
)

translation_builder = StateGraph(State)
translation_builder.add_node(
	"translation_supervisor_node", translation_supervisor_node
)
translation_builder.add_node("conversation_node", conversation_node)
translation_builder.add_node("media_node", media_node)
translation_builder.add_node("speech_to_text_node", speech_to_text_node)
translation_builder.add_node(
	"text_to_speech_audio_node", text_to_speech_audio_node
)
translation_builder.add_node("text_to_text_node", text_to_text_node)

translation_builder.add_edge(START, "translation_supervisor_node")
translation_graph = translation_builder.compile()

if settings.ENV_MODE == "local":
	translation_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "translation_graph.png"
		)
	)


def call_translation_graph(state: State) -> Command[Literal["translation_graph"]]:
	response = translation_graph.invoke(
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
					name="translation_graph",
					content=response["messages"][-1].content,
					additional_kwargs=response["messages"][-1].additional_kwargs,
				)
			],
		},
		goto=END,
	)
