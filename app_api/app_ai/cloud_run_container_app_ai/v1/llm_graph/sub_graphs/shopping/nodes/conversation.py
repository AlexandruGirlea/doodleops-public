import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from llm_graph.utils.conversations_state import State
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.llm_models import base_llm_vertexai

logger = logging.getLogger("APP_AI_V1_"+__name__)

conversation_template = PromptTemplate(
    input_variables=["history", "new_message", "language"],
    template="""
        You are a friendly AI shopping and selling assistant here to assist the
        user.
        To get started, you need some details from the user—what are they
        looking to buy or sell?
        If they want to buy something:
        - is it a gift, who’s it for (maybe their age or interests), and what’s th
        e occasion? Ask for the budget and if they’re shopping online or in-store.
         
         I they want to sell something:
         - what are they selling, how much do they want for it, etc.
         Do not insist on how much the user wants for it, he might not know.
         
         Keep this conversation light, short and fun.

        Guide the user step-by-step to nail this!

        Do not insist on getting all the information if the user does not want to
        provide it. You can try to fill in the gaps and ask for user confirmation.

        This is the conversation so far:
        {history}

        Now, the user says:
        {new_message}

        VERY IMPORTANT: DO NOT help the user search for illegal products or 
        services. Politely steer the conversation in the right direction if the
        user asks for such products
        
        To help you formulate a better response, be aware that we also offer other
        services like product research and web search where to buy or sell
        products, but that is done by other assistants so inform the user that
        we can help with that if needed.
        
        Your entire purpose is just to understand the user's needs and
        preferences, guide the conversation, and gather the necessary
        information but NOT to suggest any products or services.

        Respond in the language {language}.
        """
)

shopping_chain = conversation_template | base_llm_vertexai


def conversation_node(state: State) -> Command[Literal["conversation_node"]]:
    language = state.get("language", "english")
    messages = get_historical_and_new_msg(state=state)
    history = messages["history"]
    new_message = messages["new_message"]
    extraction_result = shopping_chain.invoke(
        {
            "history": str(history), "new_message": str(new_message),
            "language": language
        }
    )
    return Command(
        update={
            "messages": [
                AIMessage(
                    content=extraction_result.content, name="conversation_node"
                )
            ]
        },
        goto=END
    )
