import logging
from typing import Literal
from datetime import datetime

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


from core import settings
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.translation import translate
from llm_graph.utils.conversations_state import State
from llm_graph.utils.video_logic import generate_video
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg
from common.redis_utils import update_user_msgs, does_user_have_enough_credits


logger = logging.getLogger("APP_AI_V1_" + __name__)


image_to_video_schemas = [
	ResponseSchema(
		name="process_media", type="bool",
		description=(
			"Set to *True* if a valid image media file (image: JPG, JPEG, PNG) "
			"is provided in the conversation history or latest message and should "
			"be processed. Set to *False* if no media is provided, the file type "
			"is unsupported, or processing isn’t needed."
		)
	),
	ResponseSchema(
		name="media_prompt", type="str",
		description=(
			"If `process_media` is *True*, provide a short but descriptive prompt "
			"in *English* for processing the image to video as the user requested. "
			"Do not add any extra conversation information to the prompt."
		)
	),
	ResponseSchema(
		name="media_link", type="str",
		description=(
			"If `process_media` is *True*, provide the exact URL of the media file "
			"(image) to process, as found in the conversation history or "
			"latest messages. Do not modify the URL or add extra characters. This "
			"link will be used to download the media file."
		)
	),
	ResponseSchema(
		name="user_response", type="str",
		description=(
			"If `process_media` is *False*, provide a polite and concise response "
			"to the user explaining why the media could not be processed or what "
			"is needed to proceed. Tailor the response to the situation:\n"
			"- If no media file is provided in the conversation history or latest "
			"message, politely inform the user that an image file is required and "
			"specify the supported formats (image: JPG, JPEG, PNG). "
			"Example: `I couldn't identify the media file in your message. "
			"Please provide an image (JPG, JPEG, PNG) so I can assist "
			"you.`\n"
			"- If a media file is provided but it's an unsupported type, explain "
			"that the format isn't supported and list the accepted formats. "
			"Example: `The file you provided isn’t in a supported format. I can "
			"only process JPG, JPEG, PNG files. Please upload one of "
			"these.`\n"
			"- If a media file is present but processing isn’t appropriate (e.g., "
			"additional details are needed), clarify why and guide the user. "
			"Example: `I have a media file, but I need more details to process "
			"it. How would you like to animate it?`"
			"Keep the response helpful, concise (max 100 words). "
			"Response should be in {language}."
		)
	),
]

image_to_video_parser = StructuredOutputParser.from_response_schemas(
	image_to_video_schemas)
image_to_video_instructions = image_to_video_parser.get_format_instructions()

image_description_template = PromptTemplate(
	input_variables=["history", "new_message", "language", "format_instructions"],
	template="""
		You are a AI assistant that can identify image urls provided by the user
		and respond with a video prompt for generating a video based on that
		image.

		**Your Tasks:**

		1. **Check for Media File:**
		- Examine the conversation history and the latest user message for a media
		file link (image: JPG, JPEG, PNG) the user might be referencing.
		- If a valid, relevant media link is found, set `process_media` to True.
		Do not ask for a media file if one has already been provided.
		- If multiple media links exist, select the most recent or relevant one.
		Process only one file at a time.
		- Decline unsupported file types (e.g., videos) politely, saying,
		"I can only process images (JPG, JPEG, PNG) for now."
		
		2. **Provide Media Prompt (if processing media):**
		- If `process_media` is True, craft a short but descriptive `media_prompt`
		in English for the image to video processor, based on the user's request.
		
		3. **Provide User Response (if not processing media):**
		- If `process_media` is False, provide a `user_response` telling the user
		that you could not process the media or you need the file to proceed,
		which ever applies.
		- Use *italics*, **bold** and ```monospace``` as needed
		with Markdown syntax, but do not use other Markdown elements
		(e.g., links). If a URL is essential, include it as plain text
		(e.g., https://example.com) without formatting.
		- Max response length is 300 words.
		
		Example response to process media:
		- `process_media`: True
		- `media_prompt`: Make the people in the image smile and wave to the camera
		- `media_link`: https://example.com/image.jpg
		- `user_response`: None
		
		Example response to not process media:
		- `process_media`: False
		- `media_prompt`: None
		- `media_link`: None
		- `user_response`: I couldn't identify the media file in your message.
		
		All fields need to be filled in for the response to be valid.

		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		
		**Limitations:**
		- you can't animate images with children or teenagers
		- you can't provide nudes or sexual content
		""",
)

image_to_video_chain = (
		image_description_template | base_llm_vertexai | image_to_video_parser
)


def image_to_video_node(state: State) -> Command[Literal["image_to_video_node"]]:
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
						name="image_to_video_node"
					)
				]
			},
			goto=END
		)
	
	messages = get_historical_and_new_msg(state=state)
	
	json_resp = image_to_video_chain.invoke(
		{
			"history": str(messages["history"]),
			"new_message": str(messages["new_message"]),
			"language": language,
			"format_instructions": image_to_video_instructions
		}
	)
	
	media_link = json_resp.get("media_link")
	media_prompt = json_resp.get("media_prompt")
	user_response = json_resp.get("user_response")
	if json_resp.get("process_media") and media_prompt and media_link:
		if state.get("user_phone_number"):
			send_whatsapp_message(
				to_phone_number=state.get("user_phone_number"),
				body=translate(
					msg="Give me a few seconds to generate the video for you.",
					language=language
				)
			)
			
		video_url = generate_video(prompt=media_prompt, image_url=media_link)
	
		if not video_url:
			error_msg = "Sorry, I couldn't generate that video. Please rephrase."
			return Command(
				update={
					"messages": [
						AIMessage(
							content=translate(msg=error_msg, language=language),
							name="image_to_video_node"
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
			error_msg = "Sorry, I couldn't send the video. Please try again."
			return Command(
				update={
					"messages": [
						AIMessage(
							content=translate(msg=error_msg, language=language),
							name="image_to_video_node"
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
					f"Video prompt generated: {media_prompt}. "
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
						name="image_to_video_node",
						additional_kwargs={
							"generate_video": all_llm_costs.generate_video
						}
					)
				]
			},
			goto=END
		)
	
	if not user_response:
		user_response = (
			"Sorry, I couldn't generate that video. Please try again later."
		)
	
	return Command(
		update={
			"messages": [
				AIMessage(
					content=translate(
						msg=user_response,
						language=language
					),
					name="image_to_video_node",
				)
			]
		},
		goto=END
	)
