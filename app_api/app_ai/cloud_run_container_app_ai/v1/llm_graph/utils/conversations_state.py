from typing import Optional

from langgraph.graph import MessagesState

from common.pub_sub_schema import LLMCost


class State(MessagesState):
	"""
	A simple state carrying a list of messages and a 'next' field for routing.
	An optional 'user_phone_numer' field is also included for context.
	An optional 'language' field is also included for context.
	An optional 'username' field is also included for context.
	"""
	next: str
	username: Optional[str] = None
	user_phone_number: Optional[str] = None
	language: Optional[str] = None
	all_llm_costs: LLMCost = LLMCost()
	user_total_available_credits: Optional[int] = None
	has_metered_subscription: Optional[bool] = None
