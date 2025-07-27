import logging
from typing import List

from pydantic import BaseModel, Field
from fastapi import Depends, HTTPException, status, Request, Form

from core.settings import GENERIC_ERROR_MSG
from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from common.other import get_filename_from_cd
from schemas.openai import OpenAIFileIdRef, ResponseModel
from common.openai.fastapi_transaltion import (
	get_file_from_request, upload_resp_file_content_to_bucket
)
from app_pdf.views.v1.openai_views.route import v1_view_pdf_router_openai
from app_pdf.views.v1.base_logic.pdf_password_management_remove import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


class RequestModel(BaseModel):
	password: str = Field(
		...,
		min_length=1,
		max_length=50,
		description="Password to be added to the PDF file",
	)
	openaiFileIdRefs: List[OpenAIFileIdRef]


@v1_view_pdf_router_openai.post(
	f"{URL_DATA.api_url}/openai",
	include_in_schema=True,
	description=(
			"Accepts a list of openaiFileIdRefs containing exactly one PDF file, "
			"and a password parameter, and removes the password from the PDF "
			"file. Responds with a download link for the output PDF file. Max "
			"file size is 10MB, and download link expires in 5 minutes."
	),
	summary="Remove password from PDF",
)
async def view_pdf_password_management_remove_openai(
		request: Request,
		request_model: RequestModel,
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
) -> ResponseModel:
	files = await get_file_from_request(
		request=request,
		api_name=API_NAME,
		username=token_data.username,
	)
	file = files[0]

	resp = await get_cloud_run_response(
		token_data=token_data,
		redis_conn=redis_conn,
		file=file,
		password=request_model.password,
	)
	del file
	if resp.status_code == 400:
		return resp

	try:
		headers = {k.lower(): v for k, v in resp.headers.items()}
		filename = get_filename_from_cd(headers=headers)

		file_url = upload_resp_file_content_to_bucket(
			resp_file_content=resp.body,
			filename=filename,
			content_type=resp.headers.get("content-type"),
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
