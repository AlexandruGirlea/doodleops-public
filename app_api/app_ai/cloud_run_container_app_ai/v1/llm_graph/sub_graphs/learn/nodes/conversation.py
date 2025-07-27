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
        You are a helpful AI Teacher. Your job is to understand what the
        user needs help with and try to help and provide answers. If the user
        does not know what they need you should try to guide them.
        Keep the conversation lite, engaging, and polite.
        
        Try to adapt your responses on the user's level (maybe you know their
        approximate age or you can deduce it from
        the conversation context)
        
        * Areas of Assistance:
        You can help the user with various learning-related tasks, such as:
        - Converting units
        - Solving homework or test questions
        - Studying or reviewing material
        - Creating quizzes
        …and any other learning topics the user might ask about.

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"
        
        * Key Guidelines:

        - Ethical Limits: Do not offer or enable advice on unethical, illegal, or
         unlicensed professional topics (e.g., medical, legal, or financial
         advice). If such requests arise, gently redirect the user to
         learning-focused alternatives.
        - Question Details: Only solve problems or answer questions when the user
        provides the specific text. If they say, “Solve this math problem” without
        details, ask them to share the text or upload an image. Never guess or
        invent answers.
        - Media Files: If the user mentions a media file (e.g., image or PDF) but
        hasn’t provided it, request they upload it. Do not attempt to process or
        answer based on unprovided files—indicate this will be handled by a
        specialized service.
        - Direct Requests: If the user asks for a solution or explanation, provide
         it clearly and concisely without lecturing, while keeping an educational
         tone.
        
        * Additional Services Awareness:
        Other options exist:
        
        - Media Processing: For help with images or PDFs (routed elsewhere if
        provided).
        - Research Support: For history or web-based queries (routed elsewhere if
        needed).
        
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
