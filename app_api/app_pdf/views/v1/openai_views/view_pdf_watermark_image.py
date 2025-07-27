import logging

from fastapi import Depends, HTTPException, status, Request, Query

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
from app_pdf.views.v1.base_logic.pdf_watermark_image import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


@v1_view_pdf_router_openai.post(
	f"{URL_DATA.api_url}/openai",
	include_in_schema=True,
	description=(
			"Accepts a list of openaiFileIdRefs containing exactly one PDF file, "
			"and exactly one image file (jpg, jpeg, png or svg). "
			"Responds with a download link for the output PDF file with "
			"watermark. Max PDF file size is 10MB, and download link expires in "
			"5 minutes."
	),
	summary="Add image watermark to PDF pages.",
)
async def view_pdf_watermark_image_openai(
		request: Request,
		RequestModel: RequestModel,
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		grid_rows: int = Query(
			1, title="Number of rows in the watermark grid", ge=1, le=3
		),
		grid_columns: int = Query(
			1, title="Number of columns in the watermark grid", ge=1, le=3
		),
		image_scale: float = Query(
			0.17, title="Scale factor", ge=0.05, le=1,
			description="Scale factor for the image, between 0.05 and 1"
		),
		transparency: float = Query(
			0.5, ge=0, le=1,
			description="Transparency of the watermark, between 0 and 1."
		),
):
	files = await get_file_from_request(
		request=request,
		api_name=API_NAME,
		username=token_data.username,
		max_no_of_files=2,
		min_no_of_files=2
	)

	pdf_file, image_file = (
		(files[0], files[1]) if files[0].content_type.lower() == "application/pdf"
		else (files[1], files[0])
	)

	resp = await get_cloud_run_response(
		token_data=token_data, redis_conn=redis_conn,
		grid_rows=grid_rows, grid_columns=grid_columns,
		pdf_file=pdf_file, image_scale=image_scale,
		transparency=transparency, image_file=image_file,
	)

	del pdf_file
	del image_file
	if resp.status_code == 400:
		return resp
	elif resp.status_code != 200:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=GENERIC_ERROR_MSG
		)

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
