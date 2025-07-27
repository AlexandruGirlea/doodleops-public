import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg

logger = logging.getLogger("APP_AI_V1_"+__name__)

support_conversation_template = PromptTemplate(
    input_variables=["history", "new_message", "language"],
    template="""
        You are a helpful support assistant. Your job is to understand what the
        user is looking for and guide them through the process of creating a
        ticket.
        
        You don't need any PII information from the user, just try to understand
        what they need.

        This is the conversation so far:
        {history}

        Now, the user says:
        {new_message}

        The user can:
        - Provide feedback on the service and you can create a ticket.
        - submit a support request and you can create a ticket.
        - Suggest a new feature and you can create a ticket.
        
        As you can see you can only create ticket and not help the users in any
        other way. A human assistant will take care of the rest.
        
        Inform Tte user that he can also upload any image file he thinks might
        help explain what he wants, when creating the ticket.

        Your job is to only guid the user to get him to tell you what he wants
        from a support perspective from the options above.

        If the user's request is unclear, ask them to clarify.

        Respond in the language {language}.
        """
)

support_conversation_chain = support_conversation_template | base_llm_vertexai


def support_conversation_node(
        state: State
) -> Command[Literal["support_conversation_node"]]:
    messages = get_historical_and_new_msg(state=state)
    history = messages["history"]
    new_message = messages["new_message"]

    extraction_result = support_conversation_chain.invoke(
        {
            "history": str(history), "new_message": str(new_message),
            "language": state.get("language", "english")
        }
    )

    return Command(
        update={
            "messages": [
                AIMessage(
                    content=extraction_result.content,
                    name="support_conversation_node"
                )
            ]
        },
        goto=END
    )
