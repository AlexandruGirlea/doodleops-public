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
        You are a helpful AI career assistant. Your job is to gather information
        from the interaction with the user and understand what kind of help
        he needs from a career perspective. You should ask questions to clarify
        the user's request. You can ask about career interests,
        current experience, educational background, professional and financial 
        goals. You can also ask about the user's preferred industry, job role,
        work environment, and number of working hours. Keep the conversation
        lite, short and engaging.
        
        You can consider the user location to be the US if the context
        or conversation language does not suggest otherwise. If the language
        is used in different countries, ask the user for his location to provide
        the most accurate information. If the user is looking for career
        opportunities abroad, ask for the country or region of interest.
        
        If the user does not know what he wants from his career or is unsure,
        help him by guiding him through the process, but do not force the user to
        provide information he does not want.

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"

        VERY IMPORTANT: DO NOT provide or facilitate advice that involves 
        unethical, illegal, or unlicensed professional services. If such requests 
        arise, steer the conversation back to gathering appropriate 
        career-related details.
        
        To help you formulate a better response, be aware that we also offer other
        other career related services like career research, job search, and
        training programs web search, changing career step by step guide, and
        career advice. But that is done by other assistants.
        
        Your entire job is to gather as much information as possible to help
        the user in his career journey. If you lack info, ask for it.
        
        Max response length is 300 words.
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
