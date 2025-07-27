import logging

import requests
from pydantic import BaseModel
from langchain_core.tools import tool
from googleapiclient.discovery import build
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


from core import settings
from llm_graph.utils.llm_models import base_llm_vertexai
from llm_graph.utils.translation import translate, clean_text

logger = logging.getLogger("APP_AI_V1_"+__name__)


@tool
def search_google(
		query: str, host_language_code: str, language_restrict: str,
		geolocation: str, num_results: int = 10
) -> str:
	"""
	This calls the Google Custom Search API to do a search.
	The function takes in these parameters:
	
	`query`: str -> The search query to do the google search, formulated in the
	language of the country / location we are searching in.
	
	`host_language_code`: str -> The language code of the host Example: `fr`.
	Any language code that Google supports lower case letters.
	
	`language_restrict`: str -> The language restriction of the search.
	Example: `lang_en` will restrict the search to English language you can also
	use the pipe to search in multiple languages Example: `lang_zh-TW|lang_zh-CN`
	You must use this format `lang_` followed by the language code.
	
	geolocation: str -> The geolocation of the search Example: `jp` for Japan
	
	Returns: a list of search results with these details: Title, Url, and Snippet
	as string format. The most relevant results are returned first.
	"""
	try:
		query = clean_text(query)
		
		response = requests.get(
			url="https://customsearch.googleapis.com/customsearch/v1",
			params={
				"key": settings.GCP_CUSTOM_SEARCH_API_KEY,
				"cx": settings.CUSTOM_SEARCH_ENGINE_ID,
				"safe": "active",
				"q": query,
				"num": num_results,
				"hl": host_language_code.lower(),
				"lr": language_restrict,
				"gl": geolocation.lower()
			},
		)
	
		if not response.status_code == 200:
			logger.error(
				f"Error in search_google: {response.status_code} {response.text}"
			)
			return "Sorry, I am unable to do a google search at the moment."
		json_response = response.json()
	
		items = []
		for item in json_response.get("items", []):
			items.append(
				{
					"title": item.get("title"),
					"url": item.get("link"),
					"snippet": item.get("snippet")
				}
			)
		return str(items)
	
	except Exception as e:
		logger.error(f"Error in search_google: {e}")
	
	return ""


@tool
def google_text_search_for_images(
		image_url: str,
		host_language_code: str,
		language_restrict: str,
		geolocation: str,
		num_results: int = 10
) -> str:
	"""
	This calls the Google Image Custom Search API to do a search.
	The function takes in these parameters:
	
	`image_url`: str -> The image URL to search for similar images.
	
	`host_language_code`: str -> The language code of the host Example: `fr`.
	Any language code that Google supports lower case letters.
	
	`language_restrict`: str -> The language restriction of the search.
	Example: `lang_en` will restrict the search to English language you can also
	use the pipe to search in multiple languages Example: `lang_zh-TW|lang_zh-CN`
	You must use this format `lang_` followed by the language code.
	
	geolocation: str -> The geolocation of the search Example: `jp` for Japan,
	or `us` for the United States.
	
	Returns: a list of search results with these details: Title, Url, and Snippet
	as string format. The most relevant results are returned first.
	"""
	response = requests.get(
		url="https://customsearch.googleapis.com/customsearch/v1",
		params={
			"key": settings.GCP_CUSTOM_SEARCH_API_KEY,
			"cx": settings.CUSTOM_SEARCH_ENGINE_ID,
			"q": image_url,  # Using the image URL as the search query
			"searchType": "image",  # Restricts results to images
			"num": num_results,
			"hl": host_language_code.lower(),
			"lr": language_restrict,
			"gl": geolocation.lower()
		},
	)
	if response.status_code != 200:
		logger.error(
			f"Error in search_similar_images: {response.status_code} {response.text}"
		)
		return "Sorry, I am unable to perform a similar image search at the moment."
	
	json_response = response.json()
	items = []
	for item in json_response.get("items", []):
		items.append({
			"title": item.get("title"),
			"url": item.get("image", {}).get("contextLink"),
			"snippet": item.get("snippet")
		})
	return str(items)


class YoutubeVideoData(BaseModel):
	video_link: str
	title: str
	snippet: str
	channel_title: str
	view_count: int


def youtube_search(query: str, max_results: int = 5) -> list[YoutubeVideoData]:
	"""
	This function searches for youtube videos based on the query provided.
	
	This function takes in this maine parameter:
	`query`: str -> The search query to search for youtube videos.
	
	It will return a list of youtube videos with these details:
	- Video Link
	- Title
	- Snippet
	- Channel Title
	- View Count
	
	The list is sorted based on the view count in descending order.
	"""
	youtube = build('youtube', 'v3')
	youtube_videos_response = []
	
	try:
		search_response = youtube.search().list(
			q=query,
			part='id,snippet',
			maxResults=max_results,
			type='video'  # Ensure we only return videos
		).execute()
		
		video_ids = [
			item['id'].get('videoId')
			for item in search_response.get('items', [])
		]
		
		for v_id in video_ids:
			video_response = youtube.videos().list(
				part='snippet,statistics',
				id=v_id
			).execute()
			video_data = video_response.get('items', [])[0]
			youtube_videos_response.append(YoutubeVideoData(
				video_link=f"https://www.youtube.com/watch?v={v_id}",
				title=video_data['snippet']['title'],
				snippet=video_data['snippet']['description'],
				channel_title=video_data['snippet']['channelTitle'],
				view_count=video_data['statistics']['viewCount']
			))
		
		youtube_videos_response = sorted(
			youtube_videos_response, key=lambda x: x.view_count, reverse=True
		)
	except Exception as e:
		logger.error(f"Error in youtube_search: {e}")
	
	return youtube_videos_response
	

def perplexity_search(
		system_msg: str, conversation: list, model: str, language: str
):
	if not conversation:
		logging.error("No user conversation provided")
		return translate(msg="Please provide a search query", language=language)
	
	messages = [
		{
			"role": "user" if m.type == "human" else "assistant",
			"content": m.content
		}  # we make sure the context is not too big
		for m in conversation[-settings.MAX_NUMBER_OF_HISTORY_MSGS_PERPLEXITY:]
		if m.type in {"human", "ai"}
	]
	# loop through the msgs and make sure they alternate
	clean_mgs = []
	for m in messages:
		if clean_mgs:
			if m["role"] == clean_mgs[-1]["role"]:
				continue
		clean_mgs.append(m)
	
	# make sure that the first and last messages are from the user else drop
	if clean_mgs[0]["role"] != "user":
		clean_mgs = clean_mgs[1:]
	if clean_mgs[-1]["role"] != "user":
		clean_mgs = clean_mgs[:-1]
		
	payload = {
		"model": model,
		"messages": [{"role": "system", "content": system_msg}] + clean_mgs,
		"max_tokens": 1000,
		"temperature": 0.0,  # higher values are more random
		"top_p": 0.5,
		"search_domain_filter": None,
		"return_images": False,
		"return_related_questions": False,
		"search_recency_filter": "month",
		"stream": False,
		"frequency_penalty": 1,
		# I had to deactivate this because it's only available on tier 3
		# "response_format": {"type": "text"}
	}
	
	headers = {
		"Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
		"Content-Type": "application/json"
	}
	
	url = "https://api.perplexity.ai/chat/completions"
	try:
		response = requests.post(url, json=payload, headers=headers)
		
		if response.status_code != 200 or not response.json().get("choices"):
			logger.error(f"Error in perplexity_search: {response.text}")
			return translate(
				msg=(
					"Sorry, I am unable to process your message at the moment. "
					"Please try to be more specific."
				),
				language=language,
			)
		
		json_response = response.json()
		resp = json_response.get("choices")[0].get("message", {}).get(
			"content", ""
		) + "\n\n"
		
		# append top 5 citations at the end nicely formatted
		resp += "\n".join(
			[
				f"[{i + 1}] {c}"
				for i, c in enumerate(json_response.get("citations", [])[:5])
			]
		)

		return resp
	
	except Exception as e:
		logging.error(f"Error in perplexity_search: {e}")
		return translate(
			msg=(
				"Sorry, I am unable to process your message at the moment. "
				"Please try again later."
			),
			language=language,
		)


googl_search_schemas = [
	ResponseSchema(
		name="do_search", type="bool",
		description=(
			"Set to *True* if you think that we can do a google search based "
			"on the information that we have. Set to *False* if you think "
			"that we should not proceed with the search."
		)
	),
	ResponseSchema(
		name="query", type="str",
		description=(
			"The search query to do the google search, formulated in the "
			"language of the country / location we are searching in."
		)
	),
	ResponseSchema(
		name="host_language_code", type="str",
		description=(
			"The language code of the host Example: `fr`. "
			"Any language code that Google supports lower case letters."
		)
	),
	ResponseSchema(
		name="language_restrict", type="str",
		description=(
			"The language restriction of the search. "
			"Example: `lang_en` will restrict the search to English language you "
			"can also use the pipe to search in multiple languages "
			"Example: `lang_zh-TW|lang_zh-CN` You must use this "
			"format `lang_` followed by the language code."
		)
	),
	ResponseSchema(
		name="geolocation", type="str",
		description="The geolocation of the search Example: `jp` for Japan"
	),
	ResponseSchema(
		name="user_response", type="str",
		description=(
			"If `do_search` is *False*, provide a polite and concise response "
			"to the user explaining why the search could not be done or what "
			"is needed to proceed. Tailor the response to the situation:\n"
			"For Example: If no location is provided in the conversation history "
			"or latest message, politely inform the user that a location is "
			"required. Keep the response helpful, concise (max 300 words). "
			"Response should be in {language}."
		)
	),
]

google_template = PromptTemplate(
	input_variables=[
		"history", "new_message", "language", "format_instructions",
		"additional_context"
	],
	template="""
You are a helpful google search assistant. \

You job is to understand the conversation context and formulate the best google \
search query that will help the user find the information he is looking for. \

In the query do not include any price information or to much data. You should \
include in the query the most relevant features that don't change. For example \
if the user is looking for a watch, the time of the watch is not relevant \
because it can change. \

Google search query do not work well with very specific long queries and might \
not return any results. Try to use queries like this:
- buy `product name` `location`
- shop `product name` `location`
- buy plant `plant name` `location`

VERY IMPORTANT: YOU as the assistant should formulate a search query for google \
that is most likely to return links that the user needs ONLY based on the image \
description. The query YOU formulate should not include any special characters. \
Only use alphanumeric characters and spaces.

If no location is provided in the conversation context, presume the location is \
the country that speaks the language of user conversation. If no location and \
language is associated with multiple countries (ex: spanish) DO NOT call the \
tool, ask the user for the location where to search politely and end the \
conversation there, because you are an international assistant.

If the image description tells you that the image is containing images of people \
or potential illegal content, you should not proceed with the search and inform \
the user that you can't proceed with the search.

If you have what you need call `search_google` tool to do the search.

If the location where the user is looking for the item or product, \
ex: France, Japan, etc. You should change all these parameters \
`host_language_code`, `language_restrict`, `geolocation` to the country and \
language values. We want to search for the object or item or whatever the image \
description is, in the native language of the country. Also the Query should be \
in the language of the country.

Always respond with all fields.

Example response for France can look like:
- `do_search`: True
- `query`: acheter une montre apple watch ultra 2 bracelet bleu
- `host_language_code`: fr
- `language_restrict`: lang_fr
- `geolocation`: fr
- `user_response`: none

Example response for USA can look like:
- `do_search`: True
- `query`: buy apple watch ultra 2 blue band
- `host_language_code`: en
- `language_restrict`: lang_en
- `geolocation`: us
- `user_response`: none

If you can't proceed and the user is speaking in English respond with:
- `do_search`: False
- `query`: None
- `host_language_code`: None
- `language_restrict`: None
- `geolocation`: None
- `user_response`: "Sorry, I am unable to do a web search at the moment."

for `language_restrict` you can search in multiple languages
as well by using the pipe `|` Example: `lang_zh-TW|lang_zh-CN`

Response format instructions:
{format_instructions}

Conversation history:
{history}

User’s latest message:
"{new_message}"

Additional context:
{additional_context}

Max response length is 500 words.
"""
)

google_output_parser = StructuredOutputParser.from_response_schemas(
	googl_search_schemas)

google_format_instructions = google_output_parser.get_format_instructions()

google_search_chain = (
		google_template | base_llm_vertexai | google_output_parser
)
