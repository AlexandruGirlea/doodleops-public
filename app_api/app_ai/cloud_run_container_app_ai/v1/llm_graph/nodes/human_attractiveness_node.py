import logging
from typing import Literal

from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

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
			"that will be used to process the image to assess the attractiveness "
			"of the person in the image. "
			"This prompt must always be in English. You can include relevant "
			"context from the conversation history and the latest user message, "
			"as the AI model processing the image has no other context. Start "
			"the prompt by defining the AI assistant's role and task, such as: "
			"'You are a friendly judge at a beauty contest. Your job is to "
			"evaluate the attractiveness of the person in the image and provide "
			"a score from 1 to 10, with 10 being the highest.' Instruct the AI to "
			"be polite, fair, and neutral regarding gender, race, and age. The "
			"rating should be realistic, but if the score is low, present it in "
			"an uplifting manner. If there is more than one person in the image "
			"or no person at all, decline to rate and provide an appropriate "
			"response. Always end the prompt with: 'Max response "
			"length is 300 words. Respond in this language: {language}'."
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

attractiveness_template = PromptTemplate(
	input_variables=["history", "new_message", "language", "format_instructions"],
	template="""
		You are a friendly and helpful AI beauty judge. Your job is to judge the
		attractiveness of the person in the image provided by the user.

		Your job:
			1) Determine the best action to take based on the conversation history
			and the latest user message if the image file should be processed to
			answer the user's query or not.
			You can only process image (JPG, JPEG, PNG) files for now,
			one at a time, so decline any other type of media files saying that
			you can't process them.

			The media processor is able to judge the attractiveness of the person
			in the image. Remember, if you decide
			to process the image file, the prompt should be formulated as best
			as you can.

			2) If you determine the we need to call the media processor,
			set the `process_media` variable to True and provide the prompt
			that should be used to process the image file in the
			`media_prompt` field in English.

			3) If the media file doesn't need to be processed, set the
			`process_media` variable to False and provide the `user_response`
			that should be sent to the user. In this response you can
			inform the user that you need an image file to judge the
			attractiveness of the person in the image.

		Response format instructions:
		{format_instructions}

		Conversation history:
		{history}

		User’s latest message:
		"{new_message}"
		""",
)

attractiveness_chain = attractiveness_template | base_llm_vertexai | output_parser


def human_attractiveness_node(
		state: State
) -> Command[Literal["human_attractiveness_node"]]:
	language = state.get("language", "english")
	
	messages = get_historical_and_new_msg(state=state)
	history = messages["history"]
	new_message = messages["new_message"]
	
	json_resp = attractiveness_chain.invoke(
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
					content=msg, name="human_attractiveness_node",
					additional_kwargs=cost
				)
			]
		},
		goto=END
	)
