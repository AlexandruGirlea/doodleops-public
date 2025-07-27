import logging
from typing import Literal
from datetime import datetime

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.image_logic import generate_image, ImageGenerationInput
from llm_graph.utils.llm_models import (
    base_llm_vertexai, vertex_ai_image3_model
)
from common.redis_utils import update_user_msgs
from common.other import upload_resp_file_content_to_bucket

logger = logging.getLogger("APP_AI_V1_"+__name__)

image_generator_template = PromptTemplate(
    input_variables=["history", "new_message"],
    template="""
        You are an English image prompt generator. Your job is to understand
        what the user is asking for and generate the perfect image or
        design prompt (not to short but not too long) that is descriptive enough
        for the GenAI model to generate the perfect image.

        This is the conversation so far:
        {history}

        Now, the user says (new prompt):
        "{new_message}"

        It does not matter in which language the user is speaking, you should
        generate the image prompt in English.

        Do your best and only respond with the perfect image prompt No other
        comments are needed. If the user's new prompt is a follow-up to the
        history messages, you must take that into account when generating the
        the image prompt.

        Pay attention to the context, and specify clearly in your output image
        generation prompt if the image should be black and white, gray or color.
        If color and not otherwise specified by the user, try to define it
        yourself based on the context and usual color schemes for that image
        type.
        
        If the user asks for help with a design like a logo, banner, flyer, or
        something else, make sure the name of the design is included in the
        image prompt. For example if the user wants a logo, start the prompt like
        "Generate a logo image that is ..... " and add the rest of the details.

        If the user asks for something related to popular culture but does not
        provide enough information feel free to fill in the gaps with your
        knowledge.
        
        You can't generate images with children or teenagers in them. If the user
        asks for an image with children or teenagers, do not include that in your
        image prompt answer.
        """
)

image_generator_chain = image_generator_template | base_llm_vertexai


def image_generator_node(state: State) -> Command[Literal["image_generator_node"]]:
    all_llm_costs = state.get("all_llm_costs")
    language = state.get("language", "english")

    messages = get_historical_and_new_msg(state=state)

    image_generator_result = image_generator_chain.invoke(
        {
            "history": str(messages["history"]),
            "new_message": str(messages["new_message"])
        }
    )

    if state.get("user_phone_number"):
        send_whatsapp_message(
            to_phone_number=state.get("user_phone_number"),
            body=translate(
                msg="Give me a few seconds to generate the image for you.",
                language=language
            )
        )

    img_input = ImageGenerationInput(prompt=image_generator_result.content)
    
    image_resp = generate_image(
        img_input=img_input, gcp_image_model=vertex_ai_image3_model
    )
    if not image_resp:
        error_msg = "Sorry, I couldn't generate that image. Please rephrase."
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=translate(msg=error_msg, language=language),
                        name="image_generator_node"
                    )
                ]
            },
            goto=END
        )
    img_bucket_url = upload_resp_file_content_to_bucket(
        resp_file_content=image_resp, filename="image.png",
        content_type="image/png",
    )

    resp = send_whatsapp_message(
        to_phone_number=state.get("user_phone_number"),
        media_urls=[img_bucket_url]
    )

    if not resp:
        error_msg = "Sorry, I couldn't send the image to you. Please try again."
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=translate(msg=error_msg, language=language),
                        name="image_generator_node"
                    )
                ]
            },
            goto=END
        )

    if state.get("username"):
        # We do this so that the llm has in the conversation history the img
        # prompt. We also need to add something from the user so that the
        # conversation is not empty.
        update_user_msgs(
            username=state.get("username"),
            timestamp=int(datetime.now().timestamp()),
            assistant_msg=(
                f"Image prompt generated: {image_generator_result.content}, "
                f"Image Link: {img_bucket_url}."
            ),
            user_msg="ok",
            user_is_first=False
        )

    return Command(
        update={
            "messages": [
                AIMessage(
                    content=translate(
                        msg="Here is the image you requested.",
                        language=language
                    ),
                    name="image_generator_node",
                    additional_kwargs={
                        "image_generation": all_llm_costs.image_generation
                    }
                )
            ]
        },
        goto=END
    )
