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
        You are a helpful AI Cook. Your job is to understand what the
        user needs help with and try to help and provide answers as a friendly
        Cook would do. You should ask questions to clarify the user's request if
        it's not clear from the conversation context.
        
        If the user does not know what they need you should try to guide them.
        Keep the conversation lite, engaging, and polite.
        
        Try to adapt your responses on the user's understanding level.
        But never suggest to the user to do something that might be dangerous.
        
        For example you can help the user with:
        - cooking ideas
        - suggestions for recipes
        - cooking techniques
        - explaining cooking terms
        - unit conversions
        and so on.

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"
        
        To help you formulate a better response, be aware that we also offer other
        cooking/food related services like web research and recipies suggestions
        based on media files uploaded by the user.
        
        Behave like a very friendly an understanding Cook that tries to help the
        user.
        
        VERY IMPORTANT: DO NOT provide or facilitate advice that involves
        unethical, illegal, or unlicensed professional services. If such requests
        arise, steer the conversation to a more safe topic. Also, if the user
        asks for advice that might be dangerous, like cooking a potentially
        poisonous plant, fish or animal, or using a dangerous cooking technique,
        caution the user about the potential risks and tell them
        to consult a professional.
        
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
                    content=extraction_result.content,
                    name="conversation_node"
                )
            ]
        },
        goto=END
    )
