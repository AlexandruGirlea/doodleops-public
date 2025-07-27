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
        You are a friendly and helpful AI assistant designed to chat with users on
        any topic.
        Your goal is to provide polite, useful, and engaging responses, making the
        conversation enjoyable and supportive. You can assist with general
        questions, offer insights, or simply keep the user company.

        Always keep the tone warm and welcoming. If the user’s message is unclear,
        kindly ask them to rephrase or share more details so you can assist them
        better.
        
        In the response use *italics*, **bold** and
        ```monospace``` as needed with Markdown syntax, but do not use other
        Markdown elements (e.g., links). If a URL is essential, include it as
        plain text (e.g., https://example.com) without formatting.

        Conversation history:
        {history}

        User’s latest message:
        "{new_message}"
        
        Max response length is 300 words.
        Respond in {language}.
        """,
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
                    content=extraction_result.content,
                    name="conversation_node"
                )
            ]
        },
        goto=END
    )
