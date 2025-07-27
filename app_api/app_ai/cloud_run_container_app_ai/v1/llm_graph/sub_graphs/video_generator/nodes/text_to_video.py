import logging
from typing import Literal
from datetime import datetime

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from core import settings
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.video_logic import generate_video
from llm_graph.utils.llm_models import base_llm_vertexai
from common.redis_utils import update_user_msgs, does_user_have_enough_credits

logger = logging.getLogger("APP_AI_V1_"+__name__)

video_generator_template = PromptTemplate(
    input_variables=["history", "new_message"],
    template="""
        You are an English video prompt generator. Your job is to understand
        what the user is asking for and generate the perfect video prompt
        (not to short but not too long) that is descriptive enough
        for the GenAI model to generate the perfect video.

        This is the conversation so far:
        {history}

        Now, the user says:
        "{new_message}"

        It does not matter in which language the user is speaking, you should
        generate the video prompt in English.

        Do your best and only respond with the perfect video prompt. No other
        comments are needed. If the user's new prompt is a follow-up to the
        history messages, you must take that into account when generating the
        the video prompt.

        Pay attention to the context, and specify clearly in your output video
        generation prompt if the video should be black and white, gray or color,
        or any other style the user wants. If not specified by the user, try to
        define it yourself based on the context and usual video style for that
        type.

        If the user asks for something related to popular culture but does not
        provide enough information feel free to fill in the gaps with your
        knowledge.
        
        **Limitations:**
        - You can't generate video prompts with children or teenagers
        - You can't generate video prompts with offensive or unethical content
        - You can't generate video prompts with illegal content
        
        If such content is requested, feel free to generate a video prompt that
        is more in line with the user's request but does not include the
        inappropriate content.
        """
)

video_generator_chain = video_generator_template | base_llm_vertexai


def text_to_video_node(state: State) -> Command[Literal["text_to_video_node"]]:
    all_llm_costs = state.get("all_llm_costs")
    username = state.get("username")
    language = state.get("language", "english")
    user_total_available_credits = state.get("user_total_available_credits", 0)
    has_metered_subscription = state.get("has_metered_subscription", False)

    if not does_user_have_enough_credits(
        username=username,
        api_cost=all_llm_costs.generate_video + all_llm_costs.simple_conversation,
        user_total_available_credits=user_total_available_credits,
        has_metered_subscription=has_metered_subscription
    ):
        error_msg = settings.NOT_ENOUGH_CREDITS_MSG
        if has_metered_subscription:
            error_msg = (
                "Enterprise user has reached monthly limit. To increase the "
                "limit, please contact support."
            )
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=translate(msg=error_msg, language=language),
                        name="text_to_video_node"
                    )
                ]
            },
            goto=END
        )

    messages = get_historical_and_new_msg(state=state)

    video_generator_result = video_generator_chain.invoke(
        {
            "history": str(messages["history"]),
            "new_message": str(messages["new_message"])
        }
    )

    if state.get("user_phone_number"):
        send_whatsapp_message(
            to_phone_number=state.get("user_phone_number"),
            body=translate(
                msg="Give me a few seconds to generate the video for you.",
                language=language
            )
        )

    video_url = generate_video(prompt=video_generator_result.content)
    
    if not video_url:
        error_msg = "Sorry, I couldn't generate that video. Please rephrase."
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=translate(msg=error_msg, language=language),
                        name="text_to_video_node"
                    )
                ]
            },
            goto=END
        )

    resp = send_whatsapp_message(
        to_phone_number=state.get("user_phone_number"),
        media_urls=[video_url]
    )

    if not resp:
        error_msg = "Sorry, I couldn't send the video to you. Please try again."
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=translate(msg=error_msg, language=language),
                        name="text_to_video_node"
                    )
                ]
            },
            goto=END
        )

    if state.get("username"):
        update_user_msgs(
            username=state.get("username"),
            timestamp=int(datetime.now().timestamp()),
            assistant_msg=(
                f"Video prompt generated: {video_generator_result.content}, "
                f"Video Link: {video_url}."
            ),
            user_msg="ok",
            user_is_first=False
        )

    return Command(
        update={
            "messages": [
                AIMessage(
                    content=translate(
                        msg="Here is the video you requested.",
                        language=language
                    ),
                    name="text_to_video_node",
                    additional_kwargs={
                        "generate_video": all_llm_costs.generate_video
                    }
                )
            ]
        },
        goto=END
    )
