import html

from langchain_core.prompts import PromptTemplate
from google.cloud import translate_v2


from llm_graph.utils.llm_models import lite_llm_vertexai
from llm_graph.utils.other import get_historical_and_new_msg


detect_language_template = PromptTemplate(
		input_variables=["history", "new_message"],
		template="""
		You are an AI assistant tasked with detecting the language of the
		conversation based on the latest user message and the conversation
		history. Your response should be **only** the full name of the detected
		language, such as "English" or "French."
		
		Follow these rules:
		- **Latest message priority**: Use the language of the latest user
		message. If the user switches languages in their most recent message,
		that is the new language.
		
		- **Translation requests**: If the user asks for translation services, the
		language they use to ask is their language. For example, if a user
		speaking in French asks to translate Greek text to English, the detected
		language is French.
		
		- **Ambiguous words**: If a word in the latest message could belong to
		multiple languages (e.g., "salut" in French and Romanian), check the
		previous user messages to decide. If the history is unclear, use the
		language of the latest message.
		
		- **Mixed languages**: If the conversation mixes languages, respond with
		the language of the latest user message.
		
		Previous user messages:
		{history}
		
		Latest user message:
		{new_message}
		
		**Respond only with the full name of the detected language** (e.g.,
		"English", "French"). Do not add extra text.
		"""
)
detect_language_chain = detect_language_template | lite_llm_vertexai

translate_template = PromptTemplate(
		input_variables=["message", "language"],
		template="""
		You are a friendly AI language translator. Your job is to translate
		the message to the desired language. Do not summarize or change the
		meaning of the message. Translate it as accurately as possible.
		Try to keep the format of the message the same or as close as possible
		to the original message.
		
		Message to translate:
		{message}
		
		Translate the message to the language {language}.
		
		If the message language is the same as the language you should respond
		with just respond with the original message.
		"""
)
translate_chain = translate_template | lite_llm_vertexai


def detect_language(conversation) -> str:
	messages = get_historical_and_new_msg(db_conversation=conversation)
	new_message = messages["new_message"]
	history = [m for m in messages["history"] if m[0] == "user"][:3]
	extraction_result = detect_language_chain.invoke(
			{"history": history, "new_message": new_message}
	)

	return extraction_result.content


def translate(msg: str, language: str) -> str:
	if "english" in language.lower():
		return msg

	resp = translate_chain.invoke({"message": msg, "language": language})

	return resp.content


def clean_text(text):
	import string
	allowed_punctuation = ":,." + string.digits
	return "".join(
		char for char in text
		if char.isalpha() or char in allowed_punctuation or char == " "
	)


def translate_text(text: str, target_language: str) -> str:
	"""
	Translates text into the target language using Google Cloud Translation API.
	
	Args:
	text (str): The text to be translated.
	target_language (str): The target language ISO 639-1 code (e.g., 'en', 'de').
	
	Returns:
	str: The translated text.
	"""
	text = clean_text(text)
	
	client = translate_v2.Client()
	
	result = client.translate(text, target_language=target_language)
	return html.unescape(result['translatedText'])
