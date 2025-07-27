"""
BaseMessage
├── HumanMessage	 (User inputs)
├── AIMessage		(Model responses)
├── SystemMessage	(System instructions)
└── FunctionMessage  (Function calls/returns)
"""
import os
import logging

from langgraph.errors import GraphRecursionError
from langgraph.graph import StateGraph, START

from core import settings
from common.redis_utils import get_total_call_cost
from common.pub_sub_schema import TwilioPublisherMsg, LLMCost, LLMGraphResponse
from llm_graph.utils.conversations_state import State
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.translation import detect_language, translate
from llm_graph.utils.build_supervisor_nodes import make_supervisor_node
from llm_graph.utils.other import (
	convert_db_msgs_to_llm_msgs, process_finish_condition
)
from llm_graph.utils.file_management import get_media_error_msg_for_file_type
from llm_graph.nodes.new_conversation import new_conversation_node
from llm_graph.nodes.media_interpreter_node import media_interpreter_node
from llm_graph.nodes.image_similarity_search_node import image_search_node
from llm_graph.nodes.dictionary_node import dictionary_and_spelling_node
from llm_graph.nodes.human_attractiveness_node import human_attractiveness_node
from llm_graph.nodes.health import health_node
from llm_graph.sub_graphs.career_advice.supervisor import call_career_graph
from llm_graph.sub_graphs.events.supervisor import call_events_graph
from llm_graph.sub_graphs.fashion.supervisor import call_fashion_graph
from llm_graph.sub_graphs.food.supervisor import call_food_graph
from llm_graph.sub_graphs.handyman.supervisor import call_handyman_graph
from llm_graph.sub_graphs.image_generator.supervisor import (
	call_image_generator_graph
)
from llm_graph.sub_graphs.learn.supervisor import call_learn_graph
from llm_graph.sub_graphs.plants.supervisor import call_plant_graph
from llm_graph.sub_graphs.shopping.supervisor import call_shopping_graph
from llm_graph.sub_graphs.stocks.supervisor import call_stock_graph
from llm_graph.sub_graphs.support.supervisor import call_support_graph
from llm_graph.sub_graphs.travel.supervisor import call_travel_graph
from llm_graph.sub_graphs.tech_support.supervisor import call_tech_graph
from llm_graph.sub_graphs.translator.supervisor import call_translation_graph
from llm_graph.sub_graphs.video_generator.supervisor import (
	call_video_generator_graph,
)
from llm_graph.sub_graphs.default.supervisor import call_default_graph

logger = logging.getLogger("APP_AI_V1_"+__name__)

main_supervisor_node = make_supervisor_node(
	model=base_llm_vertexai,
	members=[
		"dictionary_and_spelling_node", "health_node",
		"human_attractiveness_node", "image_search_node",
		"media_interpreter_node", "new_conversation_node",
		"career_graph", "events_graph", "fashion_graph",
		"food_graph", "handyman_graph", "image_generator_graph", "learn_graph",
		"plant_graph", "shopping_graph", "stock_graph", "support_graph",
		"travel_graph", "tech_graph", "translation_graph",
		"video_generator_graph", "default_graph",
	],
	additional_info=f"""
	- `dictionary_and_spelling_node` Route to this node if the user asks for the
	meaning of a word or phrase, or asks for help with spelling. This node will
	provide the meaning of the word or phrase, and a few examples of how it's
	used. If the user asks how to correctly spell a word or phrase, this node
	will provide the correct word or phrase. This node is not able to do
	research or search the internet. It's just a very simple AI that can help
	with spelling and dictionary definitions. This node can't process any media
	files.
	
	- `health_node` Route to this node if the user needs any medical health
	advice, where to buy medication, how to take medication, how to treat a
	disease, how to prevent a disease, etc. or psychological advice, like maybe
	they suffer from depression and need to talk. Do not route these types of
	requests to any other graph or node.
	
	- `human_attractiveness_node` Route to this node if the user wants to find
	out a rating of how attractive a person is from a image. This node can only
	process image media files and will provide a rating of how attractive the
	person is in the image. This node can't process any other media files.
	Do not route to this node if the users asks for stuff like: how do I look
	in this dress. Route to `fashion_graph` for fashion related questions.
	
	-`image_search_node` Route to this node if the user wants to find similar
	images. If the user already provided an image link, this node will call the
	internet image search tool to find similar images. If the user did not provide
	the image link but intends to do so, this tool will have a conversation with
	the user to guide him to upload the image for the image search.
	This is the only node or graph that is capable of doing image similarity
	searches online. It is not capable of understanding the image or provide
	any information about the image, it's only capable of finding similar images
	on the internet. The media file link has to be an image link, not a document.
	If the user is looking to buy a similar product to the one in the image,
	route to the `shopping_graph` for that.
	
	- `media_interpreter_node` Route to this node if the user sends a message
	that ends in with this format {settings.MEDIA_FILE_HUMAN_MSG_FORMAT} and
	it's not clear what the user wants to do with the media file. This node
	will have a conversation with the user to understand what he wants.
	Do not route to this node if it's clear what the user wants from the
	media file.
	
	- `new_conversation_node` Route to this node if the user wants to start a new
	conversation. This node will delete the previous conversation history to start
	fresh. Only call this node if it's obvious that the user wants to start a new
	conversation. A new conversation might be the user saying something like
	"let's start over" or the user switching topics completely and is not related
	to the previous conversation. This node does not process media files.
	
	-`career_graph`  Route to this graph for all user career advice needs.
	This graph can help the user with career advice, trainings, certifications,
	job search, career paths, salary negotiation, salary research,
	company information, company working environment, anything related to career
	advice. This graph can also process media files related to career advice.
	For example: CVs, resumes, cover letters, job descriptions, job offers,
	evaluate profile images, etc. It does not generate any media files.
	
	- `events_graph` Route to this graph for all user event search amd planning
	needs. It can help the user searching for cultural events in a city,
	it can help organizing events, planning events, finding event venues,
	event catering, event entertainment, event decoration, event planning,
	and so on. This event graph does not offer news related information, like
	the latest events in the world. It strictly focuses on fun events, parties,
	etc. This graph does not process media files, for that route to the
	`default_graph`.
	
	- `fashion_graph` Route to this graph for all user fashion advice needs.
	This graph can help the user with fashion advice, fashion trends, fashion
	styles, fashion research, fashion advice, like: what to wear, hair styles,
	which of these shoos match my dress, etc. This graph can also process media
	files related to fashion. This graph does not generate any media files.
	
	- `food_graph` Route to this graph for all user food advice needs.
	This graph can help the user with food advice, food recipes, food research,
	etc. This graph can also process media files related to food (ex: user
	uploads image of ingredients and asks for a recipe ideas). This graph does
	not generate any media files.
	
	- `handyman_graph` Route to this graph for all user handyman advice needs,
	like how to fix something, diy projects, home improvement, home repair, etc.
	This graph can't help with computer stuff, it's only for physical things.
	This graph can also process media files, both images and pdf related to
	handyman advice, like the user uploads or wants to upload a photo of something
	that needs fixing. This graph does not generate any media files.
	
	- `image_generator_graph` Route to this graph for all user image generation
	needs. This graph can help the user with generating images, designing logos,
	banners, flyers, blogpost images, social media post images, memes, t-shirts,
	anything that needs an image generation. Also route to this graph if the user
	would like to see how something looks like, it can generate images of how
	something looks like. Be aware that this does not generate
	SVG images. This graph can't process any media file links provided by the
	user.
	
	- `learn_graph` Route to this graph if the user needs help with any learning,
	topics like: STEM, history, geography, marketing, business, finance, art,
	quantum physics, etc. This graph can also help the user with unit
	conversion, homework help, school test preparation and so on. This graph can
	also process media files (image or pdf) provided as link by the user, to help
	solve math or other test problems in that image or pdf document. This graph
	can also help the user learn new things similar to a school teacher.
	
	- `plant_graph` Route to this graph for all user plant advice needs.
	This graph can help the user with plant advice, plant identification,
	plant care, plant research, anything related to plants.
	This graph can also only process image media files related to plants so
	route here to get answers to plant related questions from images.
	Do not route here if the user needs to know where to buy or sell plants, for
	that route to the `shopping_graph`. Do not route here if the user needs help
	with other media formats like documents or audio files, event if it's related
	to plants.
	
	- `shopping_graph` Route to this graph for all user shopping and selling
	needs (ex: object, real estate, cars, plants, pets, etc.) but it can't help
	with buying or selling medicine/drugs. This graph can help the user with
	shopping options, shopping advice, where to buy or sell and do
	shopping research. It can also help with product reviews. This graph can
	only process image media files to help the user search for products similar
	to the one in the image. Do not route here if the user needs help with other
	media formats like documents or audio files. This graph does not generate any
	media files. Very important route to this graph for all product review needs.
	This graph can provide both video and written reviews for products. If the word
	`review` (in any language) is in the user's latest request and it's related to
	a product, route to this graph.
	
	-`stock_graph` Route to this graph for all user stock market needs.
	This graph can provide the user with stock prices, stock news,
	stock predictions, stock / public company financial health,
	earnings reports, stock general information, historical trends,
	forcasting, stock indepth analysis, anything related to the stock market
	nothing more.
	
	-`support_graph` Route to this graph for all user support needs like:
	feedback, bug reports, feature suggestions, support tickets, anything related
	to support for the services we provide here, nothing more. This graph is not
	a tech support graph, it's a support graph for the services we provide in case
	the user wants to submit a bug with a the current conversation or a feature
	request or feedback. If the user provided a media file link that he needs
	help with, this node will include that in the support ticket.
	
	- `travel_graph` Route to this graph for all user travel needs.
	This graph can help the user with travel advice, travel planning, travel
	research, travel destinations, travel tips, travel recommendations, where
	to stay, where to eat, what to do, where to rent a car, boat etc. This graph
	can also process media files related to travel. This graph does not generate
	any media files.
	
	- `translation_graph` Route to this graph for all user translation needs.
	If the user provides an image and needs it translated, this graph can
	do that as well. This graph cant translate text to text, text to audio,
	audio to text and image to text. This graph can't do anything else but help
	with translation. No other node or graph can help with translation.
	Always route to this graph if the user provided an audio media file link.
	
	- `tech_graph` Route to this graph for when the user needs help fixing a tech
	problem like coding, computer, software, hardware, washing machine, etc.
	This graph can have a conversation with the user to understand the problem,
	it can research online for the best solution, it can provide step-by-step
	guidance to fix an issue, etc. This graph can also process media files related
	to tech. This graph does not generate any media files. Do not route to this
	graph for product review, shopping or selling, route to `shopping_graph` for
	that. Do not route to this graph if the user would like to create a support
	ticket, this graph can't do support related tasks for the services we offer.
	For that route to `support_graph`. Do not route to this node if the user
	mentions he would like a review of a product. This graph can't provide any
	reviews.
	
	- `video_generator_graph` Route to this graph for all user video
	generation needs. This graph can help the user with generating videos of any
	type. This graph can also take an image file as input and animate it (image
	to video). This graph can't process any other media file links provided by the
	user like audio or documents. Even if the user asks questions like: can you
	make a video? This is the graph that can answer that question.
	
	
	-`default_graph` Route to this graph if the user prompt does not fit any of
	the known categories. This is a general purpose graph that can handle any
	type of conversation and that can also interpret and process media files
	(but NOT AUDIO files), it can also do general web searches and youtube
	searches, etc. Anything that the other graphs and nodes can't handle, route
	to this graph. This graph can also have long discussion with the user about
	any topic, like life, universe, etc. as long as they are not related to
	learning. If the user wants to learn route to `learn_graph`.
	
	Context Switching:
	If a user’s new input clearly diverges from the current conversation’s
	domain—even if previous queries set a different context—the you as the router
	must re-evaluate and assign the conversation to the appropriate node. For
	instance, if a conversation started in the plant domain (e.g., “What is wrong
	with this plant?”) and the user later asks for “historical stock trends for
	Tesla,” the router should detect the clear domain change and route the
	conversation to the stock_graph. Use explicit keywords and context indicators
	(such as financial terms for stocks) to trigger this reassignment. If the new
	query is ambiguous, consider routing to `default_graph` to ask for
	clarifications.
	""",
)

super_builder = StateGraph(State)
super_builder.add_node("main_supervisor", main_supervisor_node)

# nodes
super_builder.add_node(
	"dictionary_and_spelling_node", dictionary_and_spelling_node
)
super_builder.add_node("health_node", health_node)
super_builder.add_node("human_attractiveness_node", human_attractiveness_node)
super_builder.add_node("image_search_node", image_search_node)
super_builder.add_node("media_interpreter_node", media_interpreter_node)
super_builder.add_node("new_conversation_node", new_conversation_node)

# graphs
super_builder.add_node("career_graph", call_career_graph)
super_builder.add_node("events_graph", call_events_graph)
super_builder.add_node("fashion_graph", call_fashion_graph)
super_builder.add_node("food_graph", call_food_graph)
super_builder.add_node("handyman_graph", call_handyman_graph)
super_builder.add_node("image_generator_graph", call_image_generator_graph)
super_builder.add_node("video_generator_graph", call_video_generator_graph)
super_builder.add_node("learn_graph", call_learn_graph)
super_builder.add_node("plant_graph", call_plant_graph)
super_builder.add_node("shopping_graph", call_shopping_graph)
super_builder.add_node("stock_graph", call_stock_graph)
super_builder.add_node("support_graph", call_support_graph)
super_builder.add_node("travel_graph", call_travel_graph)
super_builder.add_node("tech_graph", call_tech_graph)
super_builder.add_node("translation_graph", call_translation_graph)
super_builder.add_node("default_graph", call_default_graph)


super_builder.add_edge(START, "main_supervisor")
super_graph = super_builder.compile()

if settings.ENV_MODE == "local":
	super_graph.get_graph().draw_png(
		output_file_path=os.path.join(
			os.path.dirname(__file__), "super_graph.png"
		)
	)


def call_main_supervisor(
		messages: list[tuple[str, str]], twilio_publisher_msg: TwilioPublisherMsg,
		media_file_link: str = None,
		user_total_available_credits: int = 0,
		has_metered_subscription: bool = False,
) -> LLMGraphResponse:
	if not messages or not twilio_publisher_msg.username:
		logger.error(
			f"No messages in call_main_supervisor, messages: {messages}"
		)
		return LLMGraphResponse(
			message=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT,
			is_error=True,
		)
	try:
		llm_messages = convert_db_msgs_to_llm_msgs(db_msgs=messages)

		if not llm_messages[-1].content:
			logger.error("No content in the last message")
			return LLMGraphResponse(
				message=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT,
				is_error=True,
			)

		language = detect_language(conversation=messages)
		if twilio_publisher_msg.media_url and not media_file_link:
			error_msg = get_media_error_msg_for_file_type(
				mime_type=twilio_publisher_msg.media_type
			)
			return LLMGraphResponse(
				message=translate(msg=error_msg, language=language),
				is_error=True,
				total_call_cost=(
					twilio_publisher_msg.all_llm_costs.simple_conversation
				)
			)
			
		graph_resp = super_graph.invoke(
			input={
				"messages": llm_messages,
				"user_phone_number": twilio_publisher_msg.phone_number,
				"username": twilio_publisher_msg.username,
				"language": language,
				"all_llm_costs": twilio_publisher_msg.all_llm_costs,
				"user_total_available_credits": user_total_available_credits,
				"has_metered_subscription": has_metered_subscription,
			},
			config={"recursion_limit": 40},
		)

		result = process_finish_condition(
			llm_messages=llm_messages, graph_resp=graph_resp, language=language
		)
		
		total_call_cost = get_total_call_cost(
			default_costs=twilio_publisher_msg.all_llm_costs,
			all_llm_costs=LLMCost(**result["messages"][-1].additional_kwargs),
		)

		return LLMGraphResponse(
			message=result["messages"][-1].content,
			is_error=False,
			total_call_cost=total_call_cost
		)
	except GraphRecursionError as e:
		logger.error(f"Recursion error in call_main_supervisor: {e}")
		return LLMGraphResponse(
			message=settings.GENERIC_RECURSION_ERROR_MSG,
			is_error=True,
		)
	except Exception as e:
		logger.error(f"Error in call_main_supervisor: {e}")
		return LLMGraphResponse(
			message=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT,
			is_error=True,
		)
