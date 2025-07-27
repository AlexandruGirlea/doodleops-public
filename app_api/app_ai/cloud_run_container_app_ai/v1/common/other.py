import random
import string
from urllib.parse import urlparse, urljoin

import requests
from google.cloud import storage

from core.settings import TEMP_API_FILES_BUCKET, BUKET_BASE_URL


def is_valid_url(url: str) -> bool:
	try:
		result = urlparse(url)
		return all([result.scheme, result.netloc])
	except ValueError:
		return False


def random_name_generator(length: int = 5) -> str:
	return "".join(
		random.choices(
			string.ascii_uppercase + string.digits + string.ascii_lowercase,
			k=length
		)
	)


def download_image(url: str) -> tuple[bytes, str]:
	"""
	Download the image from the provided URL and return its content as bytes.
	"""
	file_type = url.split(".")[-1]
	if file_type.lower() not in ["jpg", "jpeg", "png"]:
		raise ValueError("Unsupported file type")
	elif file_type.lower() in ["jpg", "jpeg"]:
		mime_type = "image/jpeg"
	else:
		mime_type = "image/png"
	
	response = requests.get(url)
	response.raise_for_status()  # Raise an exception if the download failed
	return response.content, mime_type


def upload_resp_file_content_to_bucket(
		resp_file_content: bytes, filename: str, content_type: str,
) -> str:
	folder_name = random_name_generator(length=10)

	blob_name = f"temp/{folder_name}/{filename}"

	storage_client = storage.Client()
	bucket = storage_client.bucket(TEMP_API_FILES_BUCKET)
	blob = bucket.blob(blob_name)
	blob.upload_from_string(resp_file_content, content_type=content_type)

	return urljoin(BUKET_BASE_URL, blob_name)
