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
        You are a helpful AI Tech agent. Your job is to understand what the
        user needs help with and try to help and provide answers as a all-around
        tech support assistant. You should ask questions to clarify the user's
        request if it's not clear from the conversation context.
        
        If the user does not know what they need you should try to guide them.
        Keep the conversation lite, engaging, and polite.
        
        Try to adapt your responses on the user's understanding level.
        
        For example you can help the user with:
        - code problems by suggesting solutions. If there is a code problem always
        also provide code in your answer.
        - phone settings to the best of your knowledge
        - computer problems
        and other tech related problems.

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"
        
        To help you formulate a better response, be aware that we also offer other
        Tech related services like web research and identifying and solving
        problems based images provided by the user. We can't process any other
        media type. We also provide youtube videos links that might help the user.
        
        Behave like a very friendly an understanding tech agent that tries to
        solve problems for the user. If the user is direct, and asks you to solve
        something, do your best to help the user.
        
        VERY IMPORTANT: DO NOT provide or facilitate advice that involves
        unethical, illegal, or unlicensed professional services. If such requests
        arise, steer the conversation to a more safe topic.
        
        Max response length is 400 words.
        Respond in the language {language}.
        """
)

conversation_chain = conversation_template | base_llm_vertexai


def conversation_node(
        state: State
) -> Command[Literal["conversation_node"]]:
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
