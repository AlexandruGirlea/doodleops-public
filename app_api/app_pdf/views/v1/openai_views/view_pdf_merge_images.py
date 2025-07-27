import logging

from fastapi import Depends, Query, HTTPException, status, Request

from core.settings import GENERIC_ERROR_MSG

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from common.other import get_filename_from_cd
from schemas.openai import RequestModel, ResponseModel
from common.openai.fastapi_transaltion import (
	get_file_from_request, upload_resp_file_content_to_bucket
)
from app_pdf.views.v1.openai_views.route import v1_view_pdf_router_openai
from app_pdf.views.v1.base_logic.pdf_merge_images import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


@v1_view_pdf_router_openai.post(
	f"{URL_DATA.api_url}/openai",
	include_in_schema=True,
	description=(
			"Accepts a list of openaiFileIdRefs containing one or max 10 image "
			"files, and combines them into one PDF file. "
			"The API responds with a download link for the output PDF file. "
			"Download link expires in 5 minutes."
	),
	summary="Merge multiple images into one PDF",
)
async def view_pdf_merge_images_openai(
		request: Request,
		RequestModel: RequestModel,
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		use_upload_order: bool = Query(
			False,
			description=(
					"Single optional parameter. Ask the user if they want to "
					"merge the images in the order they uploaded them or we "
					"should order them by name."
			)
		),
):
	files = await get_file_from_request(
		request=request,
		api_name=API_NAME,
		username=token_data.username,
		max_no_of_files=10,
		min_no_of_files=1,
	)

	resp = await get_cloud_run_response(
		token_data=token_data,
		redis_conn=redis_conn,
		files=files,
		use_upload_order=use_upload_order,
	)
	del files
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
