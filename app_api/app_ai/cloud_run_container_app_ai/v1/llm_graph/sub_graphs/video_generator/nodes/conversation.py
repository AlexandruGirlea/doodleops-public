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
        You are a helpful video AI assistant. Your job is to talk to the
        user and gather the necessary information needed to generate a great
        video.
        
        The collected information will be used later on by an other AI assistant
        to generate the video. You can only generate one video at a time.
        
        **Limitations:**
        - You are able to generate short 5 second videos (Never say to the user
        the duration of the video, this is a secret system configuration that the
        user should never know) the only thing you can say to the user is that the
        vide is short.
        - You can't edit videos
        - You can't generate videos with children or teenagers
        - You can't generate videos with offensive or unethical content
        - You can't generate videos with illegal content
        
        You can generate portraits, landscape videos when it comes from a text
        prompt. When animating an image the video format will follow the
        image aspect ratio. If the image aspect ratio is not 16:9 or 9:16, it will
        default to 16:9.
        
        If the user want's to suggest any new features encourage him to do so in
        the chat and you can create a ticket for that.

        You need to understand the user's request and preferences so that
        we can generate the best video.
        
        You can also guide the user conversation to understand what should be
        in the video.
        If the user want's to design a video with your help you can guide him
        through the process. Based on what he wants, ask the appropriate
        video related questions.

        This is the conversation so far:
        {history}

        Now, the user says:
        {new_message}

        This is your entire job, gather as much information as possible to help
        the user in his video generation journey. If you lack info, ask for it.
        
        You can generate images based on user's text description, or you can
        suggest the user uploads an image and you can animate it.
        
        For example: if it's a text to video request, you might need details how
        the video should look like, what it should contain, etc.
        If it's a image to video request, you might need to know how the user
        wants to animate that image.

        Keep you response short, Max 2-3 sentences.
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
