from typing import Literal

from typing_extensions import TypedDict
from langgraph.types import Command
from langgraph.graph import END
from langchain_core.messages import SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from llm_graph.utils.conversations_state import State


def make_supervisor_node(
		model: BaseChatModel, members: list[str], additional_info: str = "",
):
	options = ["FINISH"] + members
	system_prompt = f"""You are a supervisor tasked with managing a conversation 
		between the following workers: {members}. Based on the entire conversation 
		history, determine which worker should handle the user's needs next. 
		Each worker will perform a task and respond with their results and status.
		
		Consider the entire conversation history, with recent messages providing 
		the most up-to-date information, but ensure that the overall context is 
		taken into account. If the user repeats information or provides 
		clarifications, integrate that into the existing context rather than 
		treating it as a new request.
	""" + additional_info + " When finished, respond with FINISH."

	class Router(TypedDict):
		"""Worker to route to next. If no workers needed, route to FINISH."""
		next: Literal[*options]

	def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
		messages = [
					SystemMessage(content=system_prompt)
		] + state["messages"]

		response = model.with_structured_output(Router).invoke(messages)

		goto = response.get("next")
		if not goto:
			goto = response.get("properties", {}).get("next")

		if goto == "FINISH":
			goto = END

		return Command(goto=goto, update={"next": goto})

	return supervisor_node
