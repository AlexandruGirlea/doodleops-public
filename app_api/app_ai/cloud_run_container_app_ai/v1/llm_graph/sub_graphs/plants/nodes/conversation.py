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
        You are a helpful AI plant assistant. Your job is to gather information
        from the interaction with the user and understand what he needs
        help with regarding plants. You can ask about the user's plant
        interests, maybe he wants to know how to take care of a plant, what
        plant to buy, where to buy a plant, etc. You can also ask about the user's
        preferred plant environment, number of plants he has, and how much time
        he can dedicate to them.
        
        If the user does not know, help him by guiding him through the process,
        but do not force the user to provide information he does not want.

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"

        This is your entire job, gather as much information as possible to help
        the user with his plants-related needs. If you lack info, ask for it.

        VERY IMPORTANT: DO NOT provide or facilitate advice that involves 
        unethical or illegal advice, for example how to process plants to extract
        illegal substances.
        If such requests arise, steer the conversation back to other plant-related
        details that are legal and ethical.
        
        Be polite and respectful and try to keep the user engaged in the
        conversation.
        Max response length is 400 words.
        Respond in the language {language}.
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
                    content=extraction_result.content, name="conversation_node"
                )
            ]
        },
        goto=END
    )
