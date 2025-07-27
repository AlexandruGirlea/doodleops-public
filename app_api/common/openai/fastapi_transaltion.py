import re
import uuid
import logging
from io import BytesIO
from urllib.parse import urljoin

import httpx
from google.cloud import storage
from fastapi import Request, HTTPException
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile as StarletteUploadFile

from core.settings import TEMP_API_FILES_BUCKET, BUKET_BASE_URL, ENV_MODE


logger = logging.getLogger("APP_API_"+__name__)


HEADERS = {
			"User-Agent": (
				"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
				"AppleWebKit/537.36 (KHTML, like Gecko) "
				"Chrome/115.0.0.0 Safari/537.36"
			),
			"Accept": (
				"text/html,application/xhtml+xml,application/xml;"
				"q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
				"application/signed-exchange;v=b3;q=0.9"
			),
			"Accept-Language": "en-US,en;q=0.9",
			"Accept-Encoding": "gzip, deflate, br",
			"Connection": "keep-alive",
		}


async def download_file_from_request(file_ref: dict):
	if "download_link" not in file_ref:
		raise HTTPException(
			status_code=400, detail="Invalid request, missing download_link."
		)
	elif "mime_type" not in file_ref:
		raise HTTPException(
			status_code=400, detail="Invalid request, missing file type."
		)

	async with httpx.AsyncClient(headers=HEADERS) as client:
		response = await client.get(file_ref.get("download_link"))
		response.raise_for_status()
		pdf_content = response.content

	if not pdf_content:
		raise HTTPException(
			status_code=400,
			detail="Invalid request, could not download the file."
		)

	file_like = BytesIO(pdf_content)
	file = StarletteUploadFile(
		filename=(
			file_ref.get("name") if file_ref.get(
				"name") else "uploaded.pdf"
		),
		file=file_like
	)
	file.headers = Headers({"content-type": file_ref.get("mime_type")})

	return file


async def get_file_from_request(
		request: Request, api_name: str, username: str = "unknown",
		max_no_of_files: int = 1, min_no_of_files: int = 1
) -> list:
	req = await request.json()
	if not req.get("openaiFileIdRefs"):
		raise HTTPException(
			status_code=400,
			detail="Invalid request, missing file."
		)
	openai_field_refs = req.get("openaiFileIdRefs")

	if len(openai_field_refs) > max_no_of_files:
		raise HTTPException(
			status_code=400,
			detail="Only one file or openaiFileIdRefs is allowed."
		)
	elif len(openai_field_refs) < min_no_of_files:
		raise HTTPException(
			status_code=400,
			detail=(
				f"At least {min_no_of_files} files are required."
				if min_no_of_files > 1 else "File is required."
			)
		)

	files = []
	try:
		for file_ref in openai_field_refs:
			file = await download_file_from_request(file_ref=file_ref)
			files.append(file)
	except Exception as error:
		logger.error(
			f"User {username} encounter an error when calling "
			f"API: {api_name}. Response: {error}."
		)
		raise HTTPException(
			status_code=400,
			detail="Invalid request, could not download the file."
		)

	return files


def sanitize_filename(filename: str) -> str:
	filename_no_spaces = filename.replace(" ", "_")
	# remove any other special chars, e.g.: and replace with underscores
	filename_no_spaces = re.sub(r"[^A-Za-z0-9._-]+", "_", filename_no_spaces)
	return filename_no_spaces


def upload_resp_file_content_to_bucket(
		resp_file_content, filename: str, content_type: str
) -> str:
	if not filename:
		raise HTTPException(
			status_code=400, detail="Invalid request, missing filename."
		)
	unique_id = "-".join([str(uuid.uuid4()) for _ in range(3)])
	filename = sanitize_filename(filename)
	blob_name = f"temp/{unique_id}/{filename}"

	if ENV_MODE != "local":
		storage_client = storage.Client()
		bucket = storage_client.bucket(TEMP_API_FILES_BUCKET)
		blob = bucket.blob(blob_name)
		blob.upload_from_string(resp_file_content, content_type=content_type)

	return urljoin(BUKET_BASE_URL, blob_name)
