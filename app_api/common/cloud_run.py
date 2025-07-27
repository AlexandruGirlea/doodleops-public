import logging
from typing import List, Literal

from httpx import AsyncClient
from fastapi import UploadFile, HTTPException, Response
from cryptography.fernet import Fernet
from starlette.datastructures import UploadFile as StarletteUploadFile

from core.settings import (
	CRYPT_SECRET_KEY_G_CLOUD_RUN, EXPECTED_TOKEN_CLOUD_RUN,
)


logger = logging.getLogger(__name__)


async def async_request(
		url: str,
		method: Literal["GET", "POST", "PUT", "DELETE"] = "POST",
		file: UploadFile | None = None,
		files: List[UploadFile] | None = None,
		override_files: List[tuple] | None = None,
		json: dict | None = None,
		data: dict | None = None,  # form data
		headers: dict | None = None,
		params: dict | None = None,  # query string params
		timeout: int = 60,
) -> Response:
	"""
	Very important, this function should always return the FastAPI Response that
	we want to pass on to the user. We only allow one file type to be returned:
	- FastAPI Response

	The override attributes are used to pass the payload directly to the function.
	"""
	files_payload = None
	if not url or not method:
		err_msg = "URL and method are required."
		logger.error(err_msg)
		raise HTTPException(status_code=400, detail=err_msg)
	if file and files:
		err_msg = "Only one of file or files can be provided."
		logger.error(err_msg)
		raise HTTPException(status_code=400, detail=err_msg)

	if override_files:
		files_payload = override_files
	elif file:
		files_payload = {"file": (file.filename, await file.read(), file.content_type)}
	elif files:
		files_payload = [
			("files", (file.filename, await file.read(), file.content_type))
			for file in files
			if isinstance(file, StarletteUploadFile)
			]

	if not headers:
		try:
			token = Fernet(CRYPT_SECRET_KEY_G_CLOUD_RUN).encrypt(
							EXPECTED_TOKEN_CLOUD_RUN.encode()
						).decode()
			headers = {"Authorization": f"Bearer {token}"}
		except Exception as e:
			logger.error(f"Error while encrypting token: {e}")
			raise HTTPException(
				status_code=500, detail="Internal server error"
			)

	try:
		async with AsyncClient() as client:
			if method.upper() == "POST":
				resp = await client.post(
					url,
					files=files_payload, data=data, json=json, params=params,
					headers=headers,
					timeout=timeout
				)
			elif method.upper() == "GET":
				resp = await client.get(
					url, params=params, headers=headers, timeout=timeout
				)
			else:
				raise HTTPException(
					status_code=400, detail="Method not supported."
				)
	except Exception as e:
		logger.error(f"Error while making request to {url}: {e}", exc_info=True)
		raise HTTPException(
			status_code=500, detail="Internal server error"
		)

	# Extract content, status code, and headers from the response
	content = resp.content
	status_code = resp.status_code
	media_type = resp.headers.get('content-type')
	response_headers = dict(resp.headers)

	# Remove hop-by-hop headers that should not be forwarded
	hop_by_hop_headers = [
		'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
		'te', 'trailers', 'transfer-encoding', 'upgrade'
	]
	for header in hop_by_hop_headers:
		response_headers.pop(header, None)

	# Return a FastAPI Response with the extracted information
	return Response(
		content=content,
		status_code=status_code,
		headers=response_headers,
		media_type=media_type
	)
