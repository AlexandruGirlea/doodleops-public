import logging

from fastapi import UploadFile, File, Depends, Query

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from app_pdf.views.v1.fastapi_views.route import v1_view_pdf_router
from app_pdf.views.v1.base_logic.pdf_watermark_text import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)

MAX_TEXT_LENGTH = 25


@v1_view_pdf_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_pdf_watermark_text(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		text: str = Query(
			..., title="Text to watermark", max_length=MAX_TEXT_LENGTH
		),
		transparency: float = Query(0.5, title="Opacity", ge=0, le=1),
		grid_rows: int = Query(
			1, title="Number of rows in the watermark grid", ge=1, le=3
		),
		grid_columns: int = Query(
			1, title="Number of columns in the watermark grid", ge=1, le=3
		),
		rgb_text_color: str = Query(
			"255,255,255", title="RGB text color",
			ription="RGB color for the text in the format '255,255,255'"
		),
		rotation_angle: int = Query(0, ge=-360, le=360),
		file: UploadFile = File(...),
):
	return await get_cloud_run_response(
		token_data=token_data, redis_conn=redis_conn,
		text=text, transparency=transparency,
		grid_rows=grid_rows, grid_columns=grid_columns,
		rgb_text_color=rgb_text_color, rotation_angle=rotation_angle,
		file=file,
		)
