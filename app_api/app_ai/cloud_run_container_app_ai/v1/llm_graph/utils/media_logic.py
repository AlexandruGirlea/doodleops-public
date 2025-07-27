import logging

import requests
from pydantic import BaseModel
from vertexai.generative_models import Part
from llm_graph.utils.translation import translate

from core import settings
from common.other import is_valid_url
from common.pub_sub_schema import LLMCost
from llm_graph.utils.llm_models import media_understanding_vertexai


logger = logging.getLogger("APP_AI_V1_" + __name__)


class MediaInput(BaseModel):
	process_media: bool = False
	media_prompt: str = ""
	media_link: str = ""
	user_response: str = ""
	

class MediaResponse(BaseModel):
	msg: str = ""
	is_error: bool = False


def process_user_media_input(
		prompt: str, media_link: str = None
) -> MediaResponse:
	
	image_model = media_understanding_vertexai
	media_link = media_link.strip()
	
	r = requests.get(media_link)
	if r.status_code != 200:
		return MediaResponse(
			msg=(
				"Sorry, I couldn't process the file. Please try uploading "
				"it again."
			),
			is_error=True
		)
	
	if media_link.lower().endswith(".jpeg") or media_link.lower().endswith(".jpg"):
		mime_type = "image/jpeg"
	elif media_link.lower().endswith(".png"):
		mime_type = "image/png"
	elif media_link.lower().endswith(".pdf"):
		mime_type = "application/pdf"
	else:
		return MediaResponse(
			msg=(
				"Sorry, I couldn't process the file. Please try uploading "
				"it again."
			),
			is_error=True
		)

	try:
		image_file = Part.from_uri(uri=media_link, mime_type=mime_type)
		response = image_model.generate_content([image_file, prompt])
		return MediaResponse(msg=response.text, is_error=False)
	except Exception as e:
		logger.error(e)
		return MediaResponse(
			msg=(
				"Sorry, I couldn't process the file. Please try uploading "
				"it again. If the problem persists, you can write here a support "
				"ticket and I will create it for you."
			),
			is_error=True
		)


def get_media_response_img_or_pdf(
		media_input: dict, language: str, all_llm_costs: LLMCost
) -> tuple[str, dict]:
	process_media = media_input.get("process_media", False)
	media_prompt = media_input.get("media_prompt", "")
	media_link = media_input.get("media_link", "")
	user_response = media_input.get("user_response", "")
	
	if not isinstance(process_media, bool):
		process_media = False
	if not isinstance(media_prompt, str):
		media_prompt = ""
	if not isinstance(media_link, str):
		media_link = ""
	if not isinstance(user_response, str):
		user_response = ""
	
	media_obj = MediaInput(
		process_media=process_media, media_prompt=media_prompt,
		media_link=media_link, user_response=user_response
	)

	if media_obj.media_link.lower().endswith(".pdf"):
		cost = {
			"document_input_processing": all_llm_costs.document_input_processing
		}
	elif any(
			media_obj.media_link.lower().endswith(ext)
			for ext in [".jpeg", ".jpg", ".png"]
	):
		cost = {
			"image_input_processing": all_llm_costs.image_input_processing
		}
	elif user_response:
		return translate(msg=user_response, language=language), {}
		
	else:
		resp = translate(
			msg="I could not identify the media file.", language=language
		)
		return resp, {}
	
	if media_obj.user_response:  # if error this is the response to the user
		return media_obj.user_response, {}
	
	elif not media_obj.process_media:
		resp = media_obj.user_response
		if not resp:
			resp = translate(
				msg=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT, language=language
			)
		return resp, {}
	elif (
			media_obj.process_media and media_obj.media_prompt and
			media_obj.media_link
	):
		if not is_valid_url(media_obj.media_link):
			resp = translate(
				msg=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT, language=language
			)
			return resp, {}
		
		resp = process_user_media_input(
			prompt=media_obj.media_prompt,
			media_link=media_obj.media_link
		)
		
		if not resp.is_error:
			return resp.msg, cost
		return translate(msg=resp.msg, language=language), {}
	else:
		resp = translate(
			msg=settings.GENERIC_ERROR_MSG_CONTACT_SUPPORT, language=language
		)
	return resp, {}
