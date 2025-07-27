import os
import logging

from fastapi import status, Depends, HTTPException, Request, BackgroundTasks

from core.settings import GENERIC_ERROR_MSG
from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.other import cleanup_temp_dir
from common.redis_utils import get_redis_conn
from common.other import get_filename_from_cd
from schemas.openai import RequestModel, ResponseModel
from common.openai.fastapi_transaltion import (
	get_file_from_request, upload_resp_file_content_to_bucket
)
from app_pdf.views.v1.base_logic.pdf_convert_to_word_pro import (
	API_NAME, URL_DATA, get_response,
)
from app_pdf.views.v1.openai_views.route import v1_view_pdf_router_openai

logger = logging.getLogger(__name__)


@v1_view_pdf_router_openai.post(
	f"{URL_DATA.api_url}/openai",
	include_in_schema=True,
	description=(  # this should be max 300 characters (OpenAI limitation)
			"Accepts a list of openaiFileIdRefs containing exactly one PDF file, "
			"converts it to MS Word, and provides a download link for that "
			"MS Word file. Max PDF file size is 10MB, and download links expire "
			"in 5 minutes."
	),
	summary="Convert PDF to MS Word",
)
async def view_pdf_convert_to_word_pro_openai(
		background_tasks: BackgroundTasks,
		request: Request,
		RequestModel: RequestModel,
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
) -> ResponseModel:
	files = await get_file_from_request(
		request=request,
		api_name=API_NAME,
		username=token_data.username,
	)
	file = files[0]

	resp = await get_response(
		token_data=token_data,
		redis_conn=redis_conn,
		file=file
	)
	del file
	if resp["resp"].status_code == 400:
		return resp["resp"]

	try:
		headers = {k.lower(): v for k, v in resp["resp"].headers.items()}
		logger.info(f"Headers: {headers}")
		filename = get_filename_from_cd(headers=headers)
		temp_file_path = os.path.join(resp["temp_dir"], resp["temp_file"])
		with open(temp_file_path, "rb") as f:
			file_content = f.read()

		file_url = upload_resp_file_content_to_bucket(
			resp_file_content=file_content,
			filename=filename,
			content_type=resp["resp"].headers.get("content-type"),
		)

		return ResponseModel(
			openaiFileResponse=[file_url]
		)

	except Exception as error:
		logger.error(
			f"User {token_data.username} encounter an error when calling "
			f"API: {API_NAME}. Response: {error}."
		)
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=GENERIC_ERROR_MSG
		)
	finally:
		background_tasks.add_task(cleanup_temp_dir, resp["temp_dir"])
