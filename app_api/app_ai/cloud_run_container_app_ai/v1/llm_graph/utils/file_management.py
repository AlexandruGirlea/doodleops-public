from io import BytesIO

from pypdf import PdfReader
from pydub import AudioSegment

from core import settings
from common.pub_sub_schema import TwilioPublisherMsg
from common.twilio_utils import download_twilio_media
from common.other import upload_resp_file_content_to_bucket, random_name_generator


def validate_file_size_mb(contents: bytes, mime_type: str) -> bool:
	max_size_mb = settings.MAX_FILE_SIZES_MB_BY_TYPE.get(mime_type, 5)
	
	if len(contents) > max_size_mb * 1024 * 1024:
		return False  # File size is too large
	return True


def validate_pdf_page_length(pdf_content: bytes) -> bool:
	reader = PdfReader(BytesIO(pdf_content))
	if len(reader.pages) > settings.MAX_PDF_PAGES:
		return False
	return True


def validate_mime_type(mime_type: str) -> bool:
	parts = mime_type.lower().split("/")
	if len(parts) != 2:
		return False
	
	file_format, content_format = parts[0], parts[1]
	
	if file_format not in settings.ALLOWED_FILE_FORMATS:
		return False
	
	if content_format not in settings.ALLOWED_FILE_FORMATS[file_format]:
		return False
	return True


def get_media_error_msg_for_file_type(mime_type: str) -> str:
	if settings.SPECIFIC_ERROR_MEDIA_FILE_MSG.get(mime_type):
		return settings.SPECIFIC_ERROR_MEDIA_FILE_MSG.get(mime_type)
	
	return settings.GENERIC_ERROR_MEDIA_FILE_MSG


def process_media_url(twilio_publisher_msg: TwilioPublisherMsg) -> str:
	media_type = twilio_publisher_msg.media_type
	
	if not twilio_publisher_msg.media_url:
		return ""
	
	if not validate_mime_type(media_type):
		return ""
	
	media_content = download_twilio_media(twilio_publisher_msg.media_url)
	
	if not validate_file_size_mb(media_content, media_type):
		return ""
	
	if media_type.endswith("pdf"):
		if not validate_pdf_page_length(media_content):
			return ""
	elif any([media_type.endswith("mp3"), media_type.endswith("ogg")]):
		audio_segment = AudioSegment.from_file(
			BytesIO(media_content),
			format=twilio_publisher_msg.media_type.split("/")[-1]
		)
		if len(audio_segment) / 1000 > settings.MAX_AUDIO_LENGTH_SECONDS:
			return settings.ERROR_AUDIO_LENGTH
		output_stream = BytesIO()
		audio_segment.export(output_stream, format="flac")
		media_content = output_stream.getvalue()
		media_type = "audio/flac"
	
	# all checks passed now we upload the file to the cloud and return the link
	return upload_resp_file_content_to_bucket(
		resp_file_content=media_content,
		filename=(random_name_generator() + "." + media_type.split("/")[-1]),
		content_type=twilio_publisher_msg.media_type
	)
