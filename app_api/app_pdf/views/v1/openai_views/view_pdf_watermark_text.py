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
from app_pdf.views.v1.base_logic.pdf_watermark_text import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)

MAX_TEXT_LENGTH = 25


@v1_view_pdf_router_openai.post(
	f"{URL_DATA.api_url}/openai",
	include_in_schema=True,
	description=(
			"Accepts a list of openaiFileIdRefs containing exactly one PDF file, "
			". "
			"Responds with a download link for the output PDF file with "
			"watermark. Max PDF file size is 10MB, and download link expires in "
			"5 minutes."
	),
	summary="Add text watermark to PDF pages.",
)
async def view_pdf_watermark_text_openai(
		request: Request,
		RequestModel: RequestModel,
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		text: str = Query(
			..., title="Text to watermark", max_length=MAX_TEXT_LENGTH,
			description=f"Text to watermark, max {MAX_TEXT_LENGTH} characters."
		),
		transparency: float = Query(
			0.5, title="Opacity int between 0 an 1", ge=0, le=1,
			description=(
					"Optional parameter. Transparency of the watermark, between "
					"0 and 1."
			)
		),
		grid_rows: int = Query(
			1, title="Number of rows in the watermark grid", ge=1, le=3,
			description=(
					"Optional parameter. Number of rows in the watermark grid."
			)
		),
		grid_columns: int = Query(
			1, title="Number of columns in the watermark grid", ge=1, le=3
		),
		rgb_text_color: str = Query(
			"255,255,255", title="RGB text color",
			description="RGB color for the text in the format '255,255,255'"
		),
		rotation_angle: int = Query(
			45, ge=-360, le=360,
			description=(
					"Optional parameter. Rotation angle for the text in degrees "
					"(-360 to 360)."
			)
		),
):
	files = await get_file_from_request(
		request=request,
		api_name=API_NAME,
		username=token_data.username,
	)
	file = files[0]

	resp = await get_cloud_run_response(
		token_data=token_data, redis_conn=redis_conn,
		text=text, transparency=transparency,
		grid_rows=grid_rows, grid_columns=grid_columns,
		rgb_text_color=rgb_text_color, rotation_angle=rotation_angle, file=file,
	)
	del file
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
