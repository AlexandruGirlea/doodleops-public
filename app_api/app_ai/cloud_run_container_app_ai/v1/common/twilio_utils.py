"""
Twilio Media files:
Images: JPG, JPEG, PNG, WEBP*
Audio: OGG**, AMR, 3GP, AAC, MPEG
Documents: PDF, DOC, DOCX, PPTX, XLSX
Video: MP4 (with H.264 video codec and AAC audio)
Contacts: vCard (.vcf)
"""

import logging

import requests
from twilio.rest import Client

from core import settings


logger = logging.getLogger("APP_AI_V1_"+__name__)


def send_whatsapp_message(
		to_phone_number: str, body: str = None, media_urls: list[str] = None
) -> bool:
	if not to_phone_number:
		return False
	try:
		client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

		message_params = {
			"from_": settings.TWILIO_PHONE_NUMBER,
			"to": f"whatsapp:{to_phone_number}"
		}

		if body:
			message_params["body"] = body
		if media_urls:
			# Twilio expects media_url as a list.
			message_params["media_url"] = media_urls
		if not any([body, media_urls]):
			logger.error(f"No Body or Media url provided, {to_phone_number}")
			return False
		resp = client.messages.create(**message_params)

		logger.info(f"Sent WhatsApp message to {to_phone_number}.")
		if resp.error_code:
			logger.error(
				f"Failed to send WhatsApp to {to_phone_number} with verification "
				f"code. Error: {resp.error_message}"
			)
			return False
		return True
	except Exception as e:
		logger.error(
			f"Failed to send WhatsApp to {to_phone_number} with verification code."
			f"Error: {e}"
		)
		return False
	

def download_twilio_media(media_url: str) -> bytes:
	resp = requests.get(
		media_url, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
	)
	if resp.status_code != 200:
		logger.error(
			f"Failed to download Twilio media from {media_url}. "
			f"Status code: {resp.status_code}."
		)
		return b""
	return resp.content


def split_on_symbols(text, chunk_size=1500):
	chunks = []
	start = 0
	# Define the symbols on which to split
	symbols = {",", "\n", "?", "!", ";"}
	
	while start < len(text):
		# Skip any leading spaces to ensure progress and avoid infinite loops.
		while start < len(text) and text[start] == " ":
			start += 1
		if start >= len(text):
			break
		
		# If there are at least chunk_size characters remaining,
		# take a candidate and look for the last occurrence of any symbol.
		if start + chunk_size < len(text):
			candidate = text[start:start + chunk_size]
			idx = -1
			# Iterate backward through the candidate to find the last occurrence
			# of any symbol.
			for i in range(len(candidate) - 1, -1, -1):
				if candidate[i] in symbols:
					idx = i
					break
			
			# If no symbol is found (or it is at the very beginning),
			# default to cutting at the chunk_size.
			if idx <= 0:
				cut_point = chunk_size
			else:
				# Include the symbol in the chunk by adding 1.
				cut_point = idx + 1
			
			chunks.append(text[start:start + cut_point])
			start += cut_point
		else:
			# If fewer than chunk_size characters remain, append them all.
			chunks.append(text[start:])
			break
	
	return [c for c in chunks if c]
