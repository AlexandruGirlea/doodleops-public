import logging

from fastapi import UploadFile, File, Depends, Query

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from app_pdf.views.v1.fastapi_views.route import v1_view_pdf_router
from app_pdf.views.v1.base_logic.pdf_watermark_image import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


@v1_view_pdf_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_pdf_watermark_image(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		grid_rows: int = Query(
			1, title="Number of rows in the watermark grid", ge=1, le=3
		),
		grid_columns: int = Query(
			1, title="Number of columns in the watermark grid", ge=1, le=3
		),
		pdf_file: UploadFile = File(
			..., description="The PDF file to add the watermark to"
		),
		image_scale: float = Query(
			0.17, title="Scale factor", ge=0.05, le=1,
			description="Scale factor for the image, between 0.05 and 1"
		),
		transparency: float = Query(0.5, ge=0, le=1),
		image_file: UploadFile = File(
			..., description="The image to use as watermark (PNG, JPG, SVG)"
		),
):
	return await get_cloud_run_response(
		token_data=token_data, redis_conn=redis_conn,
		grid_rows=grid_rows, grid_columns=grid_columns,
		pdf_file=pdf_file, image_scale=image_scale,
		transparency=transparency, image_file=image_file,
	)
