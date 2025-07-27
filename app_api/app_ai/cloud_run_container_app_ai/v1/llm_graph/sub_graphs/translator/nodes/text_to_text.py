import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

from core import settings
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import lite_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg
from llm_graph.utils.translation import translate, translate_text

logger = logging.getLogger("APP_AI_V1_" + __name__)

response_schemas = [
	ResponseSchema(
		name="language_code_iso_639_1", type="str",
		description=(
			"The language the user wants to translate the text to, in "
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

text_to_text_template = PromptTemplate(
	input_variables=["history", "new_message", "format_instructions"],
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
		into, so you can populate the `language_code_iso_639_1` field

		Example response formated response:
		"language_code_iso_639_1": "ro",
		"text_to_translate: "Hi, where can I find a restaurant?"
		

		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		"""
)

text_to_text_chain = text_to_text_template | lite_llm_vertexai | output_parser


def text_to_text_node(state: State) -> Command[Literal["text_to_text_node"]]:
	language = state.get("language", "english")
	all_llm_costs = state.get("all_llm_costs")
	
	messages = get_historical_and_new_msg(state=state)
	new_message = messages["new_message"]
	history = messages["history"]
	
	dict_response = text_to_text_chain.invoke(
		{
			"history": str(history), "new_message": str(new_message),
			"format_instructions": format_instructions,
		}
	)
	
	iso_639 = dict_response.get("language_code_iso_639_1")
	text_to_translate = dict_response.get("text_to_translate")
	
	if not iso_639 or not text_to_translate:
		error = "Sorry, I couldn't understand the text you want me to translate."
		return Command(
			update={
				"messages": [
					AIMessage(
						content=translate(msg=error, language=language),
						name="text_to_text_node"
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
						name="text_to_text_node",
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
		error = "Sorry, I couldn't translate the text."
		return Command(
			update={
				"messages": [
					AIMessage(
						content=translate(msg=error, language=language),
						name="text_to_text_node"
					)
				]
			},
			goto=END
		)
	
	response = translate(msg="Here is the translated text: ", language=language)
	response += "\n" + translated_text
	
	return Command(
		update={
			"messages": [
				AIMessage(
					content=response,
					name="text_to_text_node",
					additional_kwargs={
						"text_to_text_translation": (
							all_llm_costs.text_to_text_translation
						)}
				)
			]
		},
		goto=END
	)
