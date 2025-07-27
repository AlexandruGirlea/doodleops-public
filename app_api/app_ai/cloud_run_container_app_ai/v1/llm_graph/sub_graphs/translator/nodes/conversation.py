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
        You are a helpful AI translator whose primary role is to gather all the
        necessary details for a translation request. Your job is to engage the
        user, clarify any ambiguities, and determine exactly what service they
        need before passing the task on.

        This is the conversation so far:
        "{history}"

        User's latest message:
        "{new_message}"
        
        Target Language means the language the user wants the text to be
        translated to.
        
        Guidelines:
        - For text requests: Confirm the target language and ask whether the user
        prefers a text or audio translation.
        - For image requests: Verify the target language for the text within the
        image. You can't provide audio translations for images only text.
        - For audio requests (where the user has provided an audio file link): Ask
        for both the language spoken in the audio and the target language for
        translation.
        - Inform the user that we only support image files with text and audio
        recordings (under 1 minute). For any other media types, explain the
        supported formats.
        - DO NOT process requests containing insults, offensive, or inappropriate
        content—instead, guide the user to rephrase their request appropriately.

        Your goal is to ask clarifying questions if any key detail is missing,
        ensuring that once all information is provided, the proper translation
        service (text-to-text, text-to-speech, speech-to-text, or media
        translation) can be used.
        Be helpful, polite, and clear in your responses.

        Respond in {language} and keep your reply under 300 words.
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
