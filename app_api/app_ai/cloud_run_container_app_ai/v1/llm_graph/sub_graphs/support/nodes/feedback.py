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
def feedback(user_feedback: str, user_email: str) -> str:
	"""
	Register user feedback.
	
	Args:
		user_feedback: The user's feedback.
		user_email: The user's email.
	Returns:
		A message indicating if the feedback was registered or not.
	"""
	ticker_number = create_zendesk_ticket(
		ticket_type="feedback",
		body="Feedback: "+user_feedback,
		user_email=user_email,
	)
	if ticker_number:
		return (
			f"Feedback registered with ticket number: {ticker_number}. I will "
			"send an email to you shortly to confirm the feedback."
		)

	return """
		Failed to register feedback request. Please visit our website at
		https://doodleops.com/contact/ to get in touch with us.
		"""


feedback_agent = create_react_agent(model=lite_llm_vertexai, tools=[feedback])


def feedback_node(state: State) -> Command[Literal["feedback_node"]]:
	user_email = get_user_email(state.get("user_phone_number"))
	language = state.get("language", "english")

	state["messages"] = [
		SystemMessage(
			content=f"""
			You are a helpful feedback assistant. Your job is to understand what 
			the user needs help with and if it's clear call the `feedback` tool 
			to register the user detailed request for help.
			After registering the feedback, respond to the user
			with a message that acknowledges the feedback was received and that
			it will be taken into consideration. Try to engage the user in another
			conversation based on the context.
			
			If the user sent a media file link, you should include that in
			the user feedback.
			You can't help with anything else but create a ticket.
			
			If you get a ticket number back from the `feedback` tool,
			you should include it in the response message.
			
			User Email is: {user_email}
			
			Example how to call the tool:
			- `user_feedback`: The user's feedback.
			- `user_email`: {user_email}
			
			Respond in the language {language} and provide the ticket number.
			"""
		)
	] + state["messages"]

	result = feedback_agent.invoke(
		{
			"messages": state["messages"],
			"user_email": user_email,
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=result["messages"][-1].content, name="feedback"
				)
			]
		},
		goto=END,
	)
