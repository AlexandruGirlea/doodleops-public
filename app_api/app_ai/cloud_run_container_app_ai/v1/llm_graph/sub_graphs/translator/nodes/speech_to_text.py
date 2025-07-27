"""
can return an audio file or a text, depending on what the user wants.
"""
import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from llm_graph.utils.audio import speech_to_text
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import lite_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.translation import translate, translate_text


logger = logging.getLogger("APP_AI_V1_" + __name__)

response_schemas = [
	ResponseSchema(
		name="language_code", type="str",
		description="The language of the audio file, e.g. `en-US`, `ro-RO`."
	),
	ResponseSchema(
		name="media_file_link", type="str",
		description="The link to the audio file that should be processed."
	),
	ResponseSchema(
		name="destination_language", type="str",
		description=(
			"The language the user wants to translate the audio file to in "
			"ISO 639-1 code format (e.g., 'en', 'de', 'fr')."
		)
	),
	ResponseSchema(
		name="missing_info_response", type="str",
		description=(
			"Only populate this field if there is missing "
			"any of these: audio file language, audio file, or the language to "
			"translate to. Tell the user what you need, in this "
			"language {language}. Do not ask for language codes the user will "
			"not know them, ask for the language name."
		)
	),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

speech_to_text_template = PromptTemplate(
	input_variables=[
		"history", "new_message", "format_instructions", "language"
	],
	template="""
		You are a helpful AI translator assistant.
		Your single job is to look at the conversation history and the latest
		user message and identify the language code that the audio file is in.
		
		For example if the user mentions that the audio file is in Romanian,
		then the language_code should be "ro-RO"
		
		You need to indentify the link to the audio file that should be
		provided as `media_file_link`.
		
		You also need to identify the `destination_language` that the user wants
		to translate the audio file to.
		
		It does not matter what the user conversation language is, you should
		try to identify these 3 parameters.

		Example response format for enough information:
		- "language_code": "ro-RO",
		- "media_file_link": "https://example.com/audio.mp3"
		- "destination_language: "fr"
		- "missing_info_response": ""
		
		Example response format for missing information:
		- "language_code": "ro-RO",
		- "media_file_link": "https://example.com/audio.mp3"
		- "destination_language: ""
		- "missing_info_response": "Sorry could you tell me the language you
		want to translate the audio file to?" but this should be in the language
		{language}
		
		Remember the `missing_info_response` response should always be in the
		language {language} and should ask for the missing information.

		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		"""
)

speech_to_text_chain = speech_to_text_template | lite_llm_vertexai | output_parser


def speech_to_text_node(state: State) -> Command[Literal["speech_to_text_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")
	
	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds to understand the audio file",
				language=language
			)
		)
	
	dict_response = speech_to_text_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"format_instructions": format_instructions, "language": language
		}
	)
	if dict_response.get("missing_info_response"):
		return Command(
			update={
				"messages": [
					AIMessage(
						name="speech_to_text_node",
						content=dict_response.get("missing_info_response")
					)
				]
			},
			goto=END
		)
	
	if (
			not dict_response.get("language_code") or
			not dict_response.get("media_file_link") or
			not dict_response.get("destination_language") or
			len(dict_response.get("destination_language")) != 2
	):
		error_msg = "Sorry, I could not understand the audio file or the language"
		return Command(
			update={
				"messages": [
					AIMessage(
						content=translate(msg=error_msg, language=language),
						name="in_depth_stock_analysis_node"
					)
				]
			},
			goto=END,
		)
	
	text = speech_to_text(
		language_code=dict_response["language_code"],
		media_file_link=dict_response["media_file_link"],
	)
	if not text:
		error_msg = (
			"Sorry, I could not understand the audio file, please try recording "
			"again."
		)
		return Command(
			update={
				"messages": [
					AIMessage(
						content=translate(msg=error_msg, language=language),
						name="in_depth_stock_analysis_node"
					)
				]
			},
			goto=END,
		)
	
	translated_text = translate_text(
		text=text, target_language=dict_response["destination_language"]
	)
	
	resp = translate(msg="The audio says: ", language=language) + translated_text
	
	return Command(
		update={"messages": [
			AIMessage(
				content=resp,
				additional_kwargs={
					"sound_input_processing": all_llm_costs.sound_input_processing,
				},  # we don't add `text_to_text_translation` cost here
			)  # because the cost of `sound_input_processing` is enough
		]},
		goto=END
	)
