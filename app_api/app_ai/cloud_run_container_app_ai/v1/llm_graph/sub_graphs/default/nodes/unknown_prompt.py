from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage

from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State


def unknown_prompt_node(state: State) -> Command[Literal["unknown_prompt_node"]]:
	language = state.get("language", "english")
	result = (
		"Sorry, I don't have an answer for that right now. "
		"Please try asking me something else."
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=translate(msg=result, language=language),
					name="unknown_prompt"
				)
			]
		},
		goto=END,
	)
