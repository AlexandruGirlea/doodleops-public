"""
This node is also reused by the shopping_graph.
"""

import logging
from typing import Literal
from datetime import datetime

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from common.redis_utils import update_user_msgs
from llm_graph.utils.translation import translate
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.media_logic import get_media_response_img_or_pdf
from llm_graph.utils.web_search import (
	search_google, google_search_chain, google_format_instructions
)

logger = logging.getLogger("APP_AI_V1_" + __name__)

image_response_schemas = [
	ResponseSchema(
		name="process_media", type="bool",
		description=(
			"Set to *True* if a valid media file (image: JPG, JPEG, PNG) "
			"is provided in the conversation history or latest message and should "
			"be processed. Set to *False* if no media is provided, the file type "
			"is unsupported, or processing isn’t needed."
		)
	),
	ResponseSchema(
		name="media_prompt", type="str",
		description=(
			"If `process_media` is *True*, provide a detailed prompt in *English* "
			"for processing the media file. Do not add any extra conversation "
			"information to the prompt. Then prompt should be something like this: "
			"`Focus on the main object or item in the image and return a detailed "
			"description. Try to identify brand or breed, or anything that will "
			"help the user do a google search later to find it online. Do not "
			"include any other formatting like Markdown. Max "
			"response length is 200 words. Respond in the language {language}`"
		)
	),
	ResponseSchema(
		name="media_link", type="str",
		description=(
			"If `process_media` is *True*, provide the exact URL of the media file "
			"(image) to process, as found in the conversation history or "
			"latest message. Do not modify the URL or add extra characters. This "
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
			"message, politely inform the user that a media file is required and "
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
			"it. What would you like me to do with it?`"
			"Keep the response helpful, concise (max 100 words). "
			"Response should be in {language}."
		)
	),
]

image_output_parser = StructuredOutputParser.from_response_schemas(
	image_response_schemas)
image_format_instructions = image_output_parser.get_format_instructions()

image_description_template = PromptTemplate(
	input_variables=["history", "new_message", "language", "format_instructions"],
	template="""
		You are a AI assistant that can process images and get object or \
		item descriptions.

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
		- If `process_media` is True, craft a detailed `media_prompt` in English
		for the media processor.
		
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
		- `media_prompt`: Focus on the main object or item in the image and return
		a detailed description.
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
		""",
)

image_description_chain = (
		image_description_template | base_llm_vertexai | image_output_parser
)

conversation_template = PromptTemplate(
	input_variables=["history", "new_message", "language", "web_search"],
	template="""
You are a helpful AI web search assistant. Your job is to understand what the \
user needs and assist the user.

Here is the conversation so far:
{history}

Here is the user's latest message:
{new_message}

Here are the available web search results:
{web_search}

Use the web search results to help the user find the information they need. Make \
sure to add all the relevant links, titles and descriptions to the response.

Use *italics*, **bold** and ```monospace``` as needed with Markdown syntax, but \
do not use other Markdown elements (e.g., links). Include URLs as plain text \
(e.g., https://example.com) without formatting.

Max response length is 400 words. Respond in the language {language}.
"""
)

conversation_chain = conversation_template | base_llm_vertexai


def image_search_node(state: State) -> Command[Literal["image_search_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")
	
	messages = get_historical_and_new_msg(state=state)
	history = messages["history"]
	new_message = messages["new_message"]
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds to find the best info for you",
				language=language
			)
		)
	
	img_json_resp = image_description_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"language": language, "format_instructions": image_format_instructions
		}
	)
	additional_kwargs = {}
	description = ""
	cost = {}
	media_link = img_json_resp.get("media_link")
	if (
		img_json_resp.get("process_media") and img_json_resp.get("media_prompt")
		and media_link and not img_json_resp.get("user_response")
	):
		description, cost = get_media_response_img_or_pdf(
			media_input=img_json_resp, language=language,
			all_llm_costs=state.get("all_llm_costs")
		)
	if not description or not cost:
		return Command(
			update={"messages": [
				AIMessage(
					content=translate(
						msg=(
							"I'm sorry, I could not process the image. Please "
							"try to provide a better image or ask a different "
							"question."
						),
						language=language,
					),
					additional_kwargs=additional_kwargs
				)
			]},
			goto=END
		)

	additional_kwargs = cost
	
	google_json_resp = google_search_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"language": language,
			"format_instructions": google_format_instructions,
			"additional_context": (
				f"This is the image description: \"{description}\" for the "
				f"Media file link: {media_link}. \n"
				"Formulate the best google search query based on this "
				"description."
			)
		}
	)
	
	do_search = google_json_resp.get("do_search")
	query = google_json_resp.get("query", "")
	host_language_code = google_json_resp.get("host_language_code", "")
	language_restrict = google_json_resp.get("language_restrict", "")
	geolocation = google_json_resp.get("geolocation", "")
	user_response = google_json_resp.get("user_response")
	
	if not do_search:
		if not user_response:
			return Command(
				update={"messages": [
					AIMessage(
						content=translate(
							msg=(
								"I'm sorry, I could not process the image. Please "
								"try to provide a better image or ask a different "
								"question."
							),
							language=language,
						),
						additional_kwargs=additional_kwargs
					)
				]},
				goto=END
			)
		return Command(
			update={"messages": [
				AIMessage(
					content=user_response,
					additional_kwargs=additional_kwargs
				)
			]},
			goto=END
		)
	
	elif query and host_language_code and language_restrict and geolocation:
		web_search_resp: str = search_google.invoke(
			{
				"query": query, "host_language_code": host_language_code,
				"language_restrict": language_restrict, "geolocation": geolocation
			}
		)

		additional_kwargs.update({"web_search": all_llm_costs.web_search})
		if not web_search_resp:
			return Command(
				update={"messages": [
					AIMessage(
						content=translate(
							msg=(
								"I'm sorry, I could not find any information. "
								"Please try to provide a better image or ask a "
								"different question."
							),
							language=language,
						),
						additional_kwargs=additional_kwargs
					)
				]},
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
					f"Image Link: {media_link}, "
					f"Image description: {description}, "
				)
			)
			
		# we have web search results
		extraction_result = conversation_chain.invoke(
			{
				"history": str(history), "new_message": str(new_message),
				"language": state.get("language", "english"),
				"web_search": web_search_resp
			}
		)

		return Command(
			update={
				"messages": [
					AIMessage(
						name="image_search_node",
						content=extraction_result.content,
						additional_kwargs=additional_kwargs
					)
				]
			},
			goto=END
		)
	
	return Command(
		update={"messages": [
			AIMessage(
				content=translate(
					msg=(
						"I'm sorry, I could not process the image. Please "
						"try to provide a better image or ask a different "
						"question."
					),
					language=language,
				),
				additional_kwargs=additional_kwargs
			)
		]},
		goto=END
	)
