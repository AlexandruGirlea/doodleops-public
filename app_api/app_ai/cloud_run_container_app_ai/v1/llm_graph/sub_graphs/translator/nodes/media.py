import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from llm_graph.utils.translation import translate
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.media_logic import get_media_response_img_or_pdf


logger = logging.getLogger("APP_AI_V1_" + __name__)


response_schemas = [
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
			"for processing the media file. Include relevant context from the "
			"conversation history and latest user message, as the media processor "
			"has no other context. When you start the prompt ask the AI to "
			"translate the image to a specific language. For example: greek or "
			"if the user did not specify or hinted at a language he would like "
			"the translation to be in, you can use this language {language}. "
			" End the prompt with: 'Use *italics*, **bold**, "
			"and ```monospace``` as needed with Markdown syntax, "
			"but do not use other Markdown elements (e.g., links). If a URL is "
			"essential, include it as plain text (e.g., https://example.com) "
			"without formatting. Max response length is 500 words.'"
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
			"Keep the response helpful, concise (max 300 words). "
			"Response should be in {language}."
		)
	),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

media_template = PromptTemplate(
	input_variables=["history", "new_message", "language", "format_instructions"],
	template="""
		You are a friendly and helpful AI translation assistant. Your job is to
		help the user with his translation from the image media file he provided.
		
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
		- For example: `translate this text in this image to romanian`. It does
		not matter if the user is writing in greek, your media_prompt should
		still be in English and asking for the translation in the user's desired
		language. If the user did not specified a desired language, you can use
		this language {language}.
			
		3. **Provide User Response (if not processing media):**
		- If `process_media` is False, provide a `user_response` telling the user
		that you could not process the media or you need the file to proceed,
		which ever applies.
		- Use *italics*, **bold** and ```monospace``` as needed
		with Markdown syntax, but do not use other Markdown elements
		(e.g., links). If a URL is essential, include it as plain text
		(e.g., https://example.com) without formatting.
		- Max response length is 300 words.
			
		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		""",
)

media_chain = media_template | base_llm_vertexai | output_parser


def media_node(state: State) -> Command[Literal["media_node"]]:
	language = state.get("language", "english")

	messages = get_historical_and_new_msg(state=state)
	history = messages["history"]
	new_message = messages["new_message"]
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds to understand the media file",
				language=language
			)
		)
	
	json_resp = media_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"language": language, "format_instructions": format_instructions
		}
	)
	msg, cost = get_media_response_img_or_pdf(
		media_input=json_resp, language=language,
		all_llm_costs=state.get("all_llm_costs")
	)
	
	return Command(
		update={
			"messages": [
				AIMessage(
					content=msg, name="media_node",
					additional_kwargs=cost
				)
			]
		},
		goto=END
	)
