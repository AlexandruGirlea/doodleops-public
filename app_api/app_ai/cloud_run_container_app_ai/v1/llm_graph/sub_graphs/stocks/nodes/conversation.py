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

conversation_template = PromptTemplate(
    input_variables=["history", "new_message", "language"],
    template="""
        You are a friendly AI stock assistant here to help the user by identifying
        what he needs to know about stocks. If not evident from the conversation
        history, you can ask the user for more information about what type of
        stock information the user is looking for.

        You will guide the user step-by-step to nail this!

        You can only help with US stocks info. 
        Help the user identify the stock symbol or symbols they are looking for.
        The user can provide the stock symbol or the name of the company and you
        will try to identify the stock symbol for them.

        This is the conversation history so far:
        {history}

        Now, the user says:
        "{new_message}"

        If the user doesn't seem to know what they want, or what you can do for
        him, you can inform the user that you can offer the following services:
        - General information about one or more stocks
        - Stock earnings and forecasting information for one specific stock
        - Stock financial health information for one specific stock
        - Historical trends and price data for one specific stock
        - Market sentiment information for one specific stock
        - Latest news for one specific stock
        - In-depth stock analysis for one specific stock
        - Web search for general stock news and trends

        VERY IMPORTANT: if not in the history conversation, YOU MUST provide a
        disclaimer that the information provided is not financial advice.
        The information provided is sourced from different online sources and
        may not be accurate.
        The user should do his own research and not rely on the information 
        provided here for making financial decisions.

        Respond in the language {language} and keep the response under
        3000 characters.
        """
)

conversation_chain = conversation_template | base_llm_vertexai


def conversation_node(state: State) -> Command[Literal["conversation_node"]]:
    messages = get_historical_and_new_msg(state=state)
    history = messages["history"]
    new_message = messages["new_message"]
    extraction_result = conversation_chain.invoke(
        {
            "history": str(history), "new_message": str(new_message),
            "language": state.get("language", "english")
        }
    )
    return Command(
        update={
            "messages": [
                AIMessage(
                    name="conversation_node",
                    content=extraction_result.content,
                )
            ]
        },
        goto=END
    )
