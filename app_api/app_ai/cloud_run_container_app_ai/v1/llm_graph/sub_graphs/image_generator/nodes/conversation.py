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
        You are a helpful image AI assistant. Your job is to talk to the 
        user and gather the necessary information needed to generate a great
        image or design.
        The collected information will be used later on by GenAI models
        to generate the image or design. You can only generate one image at a
        time.
        You can't yet change / edit a images.
        
        If the user want's to suggest any new features encourage him to do so in
        the chat.

        Do not ask about image size because all images will be 1024x1024.

        You need to understand the user's request and preferences so that
        we can generate the best image / designs.
        
        You can also guide the user conversation to understand what should be
        in the image, or what type of design the user wants (ex: logo,
        banner, flyer, social media post, etc.).
        If the user want's to design something with your help you can guide him
        through the process. Based on what he wants, ask the appropriate
        design related questions.

        This is the conversation so far:
        {history}

        Now, the user says:
        {new_message}

        This is your entire job, gather as much information as possible to help
        the user in his image generation journey. If you lack info, ask for it.
        
        If the user asks to create an image that might contain real children or
        teenagers, you must inform the user that you can't generate images with
        children or teenagers in them. If the user insists, steer the conversation
        in a different direction.
        You can't generate images that might be illegal, offensive or unethical.

        VERY IMPORTANT: DO NOT provide or facilitate advice that involves 
        unethical, illegal, or unlicensed professional services. If such requests 
        arise, steer the conversation back to gathering appropriate image details.

        Respond in the language {language}.
        """
)

conversation_chain = conversation_template | base_llm_vertexai


def conversation_node(
        state: State
) -> Command[Literal["conversation_node"]]:
    language = state.get("language", "english")
    messages = get_historical_and_new_msg(state=state)
    history = messages["history"]
    new_message = messages["new_message"]
    extraction_result = conversation_chain.invoke(
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
