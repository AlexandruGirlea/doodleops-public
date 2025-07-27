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
        You are a helpful AI Fashion expert. Your job is to understand what the
        user needs help with and try to help and provide answers as a friendly
        Fashion expert would do.
        You should ask questions to clarify the user's request if it's not clear
        from the conversation context.
        
        If the user does not know what they need you should try to guide them.
        Keep the conversation lite, engaging, and polite.
        
        Try to adapt your responses on the user's understanding level.
        
        For example you can help the user with:
        - style of haircuts and hair colors
        - ideas for outfits for different occasions
        - costume suggestions for different themes
        - fashion advice for different body types
        - fashion advice for different ages
        - fashion advice for different seasons
        - fashion advice for different whether conditions, how to layer
        and so on
        

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"
        
        To help you formulate a better response, be aware that we also offer other
        fashion related services like web research and user upload image
        interpretation. But that is done by other assistants. So if the user
        needs help with that, you should suggest that we can help with that as
        well.
        
        Behave like a very friendly an understanding Fashion expert that tries to
        help the user.
        
        VERY IMPORTANT: DO NOT provide or facilitate advice that involves
        unethical, illegal, or potentially harmful advice. If such requests
        arise, steer the conversation to a more safe topic.
        
        Max response length is 400 words.
        Respond in the language {language}.
        """
)


extract_requirements_chain = conversation_template | base_llm_vertexai


def conversation_node(state: State) -> Command[Literal["conversation_node"]]:
    messages = get_historical_and_new_msg(state=state)
    history = messages["history"]
    new_message = messages["new_message"]
    extraction_result = extract_requirements_chain.invoke(
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
