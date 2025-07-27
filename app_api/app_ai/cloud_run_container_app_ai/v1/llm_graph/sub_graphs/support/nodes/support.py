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
def support(user_support_query: str, user_email: str) -> str:
	"""
	Register the support request.
	
	Args:
		user_support_query: The user's support query.
		user_email: The user's email.
	
	Returns:
		A message indicating if the support request was registered or not.
	"""
	ticker_number = create_zendesk_ticket(
		ticket_type="support",
		body="Support: "+user_support_query,
		user_email=user_email,
	)
	if ticker_number:
		return (
			f"Support request registered with ticket number: {ticker_number}. I "
			"will send an email to you shortly to confirm the support request."
		)

	return """
	Failed to register support request. Please visit our website at
	https://doodleops.com/contact/ to get in touch with us.
	"""


support_agent = create_react_agent(model=lite_llm_vertexai, tools=[support])


def support_node(state: State) -> Command[Literal["support_node"]]:
	user_email = get_user_email(state.get("user_phone_number"))
	language = state.get("language", "english")

	state["messages"] = [
		SystemMessage(
			content=f"""
			You are a helpful support assistant. Your job is to understand what 
			the user needs help with and if it's clear call the 
			`support` tool to register the user detailed request for help. 
			After registering the support request, respond to the user
			with a message that the request was received and that
			we will contact them soon.
			
			If the user sent a media file link, you should include that in
			the user support query.
			
			Try to engage the user in another conversation based on the context.
			You can't help with anything else but create a support ticket.
			
			If you get a support ticket number back from the `support` tool,
			you should include it in the response message.
			
			User Email is: {user_email}
			
			Example how to call the tool:
			- `user_support_query`: The user's support query.
			- `user_email`: {user_email}
			
			Respond in the language {language} and provide the ticket number.
			"""
		)
	] + state["messages"]

	result = support_agent.invoke(
		{
			"messages": state["messages"],
			"user_email": user_email,
		}
	)
	return Command(
		update={
			"messages": [
				AIMessage(
					content=result["messages"][-1].content, name="support"
				)
			]
		},
		goto=END,
	)
