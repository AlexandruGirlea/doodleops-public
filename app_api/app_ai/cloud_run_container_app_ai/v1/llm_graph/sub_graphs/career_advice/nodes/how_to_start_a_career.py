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

how_to_start_a_career_conversation = PromptTemplate(
    input_variables=["history", "new_message", "language"],
    template="""
        You are a helpful AI career assistant. Your job is to advise the user on
        how to start a career in a specific field or industry based on the
        historical conversation.
        You should provide actionable steps, tips and tricks to help the user
        kickstart his career journey or transition to a new field. You can also
        help the user with interview tips, questions, and answers examples based
        on the user's career interests.
        Keep the conversation friendly, concise, and professional.

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"

        VERY IMPORTANT: DO NOT provide or facilitate advice that involves
        unethical, illegal, or unlicensed professional services. If such requests
        arise, steer the conversation back to gathering appropriate
        career-related details.
        
        Max response length is 300 words.
        Respond in the language {language}.
        """
)

extract_requirements_chain = (
        how_to_start_a_career_conversation | base_llm_vertexai
)


def how_to_start_a_career_node(
        state: State
) -> Command[Literal["how_to_start_a_career_node"]]:
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
                    name="how_to_start_a_career_node"
                )
            ]
        },
        goto=END
    )
