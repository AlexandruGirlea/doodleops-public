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

from core import settings
from llm_graph.utils.audio import text_to_speach
from common.twilio_utils import send_whatsapp_message
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.audio import get_list_voices_text_to_speach
from llm_graph.utils.translation import translate, translate_text

logger = logging.getLogger("APP_AI_V1_" + __name__)

DICT_OF_LANGUAGES_AND_VOICES = get_list_voices_text_to_speach()
LIST_OF_SUPPORTED_LANGUAGES = ','.join(list(DICT_OF_LANGUAGES_AND_VOICES.keys()))


response_schemas = [
	ResponseSchema(
		name="combined_language_code", type="str",
		description=(
			"The language the user wants to translate the audio file, in this "
			"format: `en-US`, `ro-RO`"
		)
	),
	ResponseSchema(
		name="language_code_iso_639_1", type="str",
		description=(
			"The language the user wants to translate the audio file to, in "
			"ISO 639-1 code format (e.g., 'en', 'de', 'fr')."
		)
	),
	ResponseSchema(
		name="text_to_translate", type="str",
		description="The text that the user wants to translate."
	),
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

text_to_speach_template = PromptTemplate(
	input_variables=[
		"history", "new_message", "format_instructions", "supported_languages"
	],
	template="""
		You are a helpful AI translator assistant.
		Your single job is to look at the conversation history and the latest
		user message and identify tha text te user want to translate and
		in which language.
		
		If you identified the text the user wants to translate populate the
		`text_to_translate` field with the text. You can rephrase so that the
		text the user wants to translate makes more sens to a foreign speaker.
		For example the user says:
		"can you ask for bread in romanian?" then the text_to_translate should be
		"where can I get bread?"
		
		of the user says: "I need help to say how much is the round brown bread in
		romanian" then the text_to_translate should be "how much is the round
		brown bread?"
		
		You also need to identify the language the user needs the text translated
		into, so you can populate the `combined_language_code` and the
		`language_code_iso_639_1`.
		
		Be aware that we only support these language codes for
		`combined_language_code`: {supported_languages}.
		
		If the desired language is not in the list you should leave the
		`combined_language_code` empty.
		
		Example response format where the translation language is in the list of
		supported languages:
		- "combined_language_code": "ro-RO",
		- "language_code_iso_639_1": "ro",
		- "text_to_translate: "Hi, where can I find a restaurant?"
		
		
		Another example where the translation language needs to be in Swahili,
		sw-TZ, which might not be a language we support for `language_code`.
		Then you should only populate the `language_code_iso_639_1`:
		- "language_code_iso_639_1": "sw",
		- "text_to_translate: "Hi, where can I find a restaurant?"

		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		"""
)

text_to_speach_chain = text_to_speach_template | base_llm_vertexai | output_parser


def text_to_speech_audio_node(
		state: State
) -> Command[Literal["text_to_speech_audio_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")
	
	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	
	if state.get("user_phone_number"):
		send_whatsapp_message(
			to_phone_number=state.get("user_phone_number"),
			body=translate(
				msg="Give me a few seconds to do the translation for you.",
				language=language
			)
		)
	
	dict_response = text_to_speach_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"format_instructions": format_instructions,
			"supported_languages": LIST_OF_SUPPORTED_LANGUAGES
		}
	)
	
	combined_language_code = dict_response.get("combined_language_code")
	iso_639 = dict_response.get("language_code_iso_639_1")
	text_to_translate = dict_response.get("text_to_translate")
	
	error = ""
	if not text_to_translate:
		error = (
			"Sorry I could not identify the text you want to translate."
			" Please type it again."
		)
	elif not iso_639:
		error = (
			"Sorry I could not identify the language you want to translate the"
			" text to. Please specify the language again."
		)
	if error:
		return Command(
			update={
				"messages": [
					AIMessage(
						name="text_to_speech_audio_node",
						content=translate(msg=error, language=language),
					)
				]
			},
			goto=END
		)
	
	if (
		len(text_to_translate) >
		settings.MAX_TEXT_LENGTH_TO_TRANSLATE_FOR_TEXT_RESPONSE
	):
		error = (
			"Sorry I can't translate text that is more than "
			f"{settings.MAX_TEXT_LENGTH_TO_TRANSLATE_FOR_TEXT_RESPONSE} "
			"characters long. Please shorten the text and try again."
		)
		return Command(
			update={
				"messages": [
					AIMessage(
						name="text_to_speech_audio_node",
						content=translate(msg=error, language=language),
					)
				]
			},
			goto=END
		)

	translated_text = translate_text(
		text=text_to_translate, target_language=iso_639
	)
	
	if not translated_text:
		error = "Sorry I could not translate the text. Please try again."
		return Command(
			update={
				"messages": [
					AIMessage(
						name="text_to_speech_audio_node",
						content=translate(msg=error, language=language),
					)
				]
			},
			goto=END
		)
	
	if (
			len(translated_text) >
			settings.MAX_TEXT_LENGTH_TO_TRANSLATE_FOR_AUDIO_RESPONSE
	):
		resp = translate(
			msg=(
				"Sorry I can't provide the audio file, it's too long. "
				"I can only provide audio files for text that is less than "
				f"{settings.MAX_TEXT_LENGTH_TO_TRANSLATE_FOR_AUDIO_RESPONSE} "
				"characters. Here is the translated text: "
			),
			language=language,
		) + translated_text
		
		return Command(
			update={
				"messages": [
					AIMessage(
						name="text_to_speech_audio_node",
						content=resp,
						additional_kwargs={
							"text_to_text_translation": (
							all_llm_costs.text_to_text_translation
							)}
					)
				]
			},
			goto=END
		)
		
	if (
			not combined_language_code or
			combined_language_code not in DICT_OF_LANGUAGES_AND_VOICES
	):
		resp = translate(
			msg=(
				"sorry I can't generate that audio file in the language you "
				"requested. Here is your text translation: "
			),
			language=language,
		) + translated_text
		
		return Command(
			update={
				"messages": [
					AIMessage(
						content=resp,
						name="text_to_speech_audio_node",
						additional_kwargs={"text_to_text_translation": (
								all_llm_costs.text_to_text_translation
							)}
					)
				]
			},
			goto=END
		)

	mp3_audio_url = text_to_speach(
		text=translated_text, language_code=combined_language_code,
		voice_name=DICT_OF_LANGUAGES_AND_VOICES[combined_language_code]
	)
	if not mp3_audio_url:
		resp = translate(
			msg=(
				"sorry I can't generate that audio file in the language you "
				"requested. Here is your text translation: "
			),
			language=language,
		) + translated_text
		
		return Command(
			update={
				"messages": [
					AIMessage(
						content=resp,
						name="text_to_speech_audio_node",
						additional_kwargs={"text_to_text_translation": (
							all_llm_costs.text_to_text_translation
						)}
					)
				]
			},
			goto=END
		)
	
	resp = send_whatsapp_message(
		to_phone_number=state.get("user_phone_number"),
		media_urls=[mp3_audio_url]
	)
	
	if not resp:
		resp = translate(
			msg=(
				"sorry I can't generate that audio file in the language you "
				"requested. Here is your text translation: "
			),
			language=language,
		) + translated_text
		
		return Command(
			update={
				"messages": [
					AIMessage(
						content=resp,
						name="text_to_speech_audio_node",
						additional_kwargs={"text_to_text_translation": (
							all_llm_costs.text_to_text_translation
						)}
					)
				]
			},
			goto=END
		)
		
	return Command(
		update={"messages": [
			AIMessage(
				content=translated_text,
				additional_kwargs={
					"respond_with_sound": all_llm_costs.respond_with_sound
				}
			)
		]},
		goto=END
	)
