from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from llm_graph.utils.other import get_user_email
from llm_graph.utils.llm_models import lite_llm_vertexai
from llm_graph.utils.conversations_state import State
from llm_graph.utils.zendesk_support import create_zendesk_ticket


@tool
def suggest_new_feature(
		user_new_feature_suggestion: str,  user_email: str
) -> str:
	"""
	Register user's new feature suggestion.
	
	Args:
		user_new_feature_suggestion: The user's new feature suggestion.
		user_email: The user's email.
	Returns:
		A message indicating if the feature suggestion was registered or not.
	"""

	ticker_number = create_zendesk_ticket(
		ticket_type="support",
		body="New Feature: "+user_new_feature_suggestion,
		user_email=user_email,
	)
	if ticker_number:
		return (
			"New feature suggestion registered with ticket number: "
			f"{ticker_number}.  I will send an email to you shortly to confirm "
			"the new feature suggestion."
		)

	return """
		Failed to register new feature suggestion request. Please visit our 
		website at https://doodleops.com/contact/ to get in touch with us. 
		We really appreciate your feedback!
		"""


suggest_new_feature_agent = create_react_agent(
	model=lite_llm_vertexai, tools=[suggest_new_feature]
)


def suggest_new_feature_node(
		state: State
) -> Command[Literal["suggest_new_feature_node"]]:
	user_email = get_user_email(state.get("user_phone_number"))
	language = state.get("language", "english")

	state["messages"] = [
		SystemMessage(
			content=f"""
			You are a helpful support assistant. Your job is to understand what 
			the user needs help with and if it's clear call the  
			`suggest_new_feature` tool to register the
			user suggestion. After registering the suggestion, respond to the user
			with a message that acknowledges the suggestion was received and that
			it will be taken into consideration.
			
			If the user sent a media file link, you should include that in
			the user suggestion.
			
			Try to engage the user in another conversation based on the context.
			You can't help with anything else but create a ticket.
			
			If you get a support ticket number back from the `support` tool,
			you should include it in the response message.
			
			User Email is: {user_email}
			
			Example how to call the tool:
			- `user_new_feature_suggestion`: The user's new feature suggestion.
			- `user_email`: {user_email}
			
			Respond in the language {language} and provide the ticket number.
			"""
		)
	] + state["messages"]

	result = suggest_new_feature_agent.invoke(
		{
			"messages": state["messages"],
			"user_email": user_email,
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=result["messages"][-1].content,
					name="suggest_new_feature"
				)
			]
		},
		goto=END,
	)
