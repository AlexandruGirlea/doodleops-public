import logging

from fastapi import UploadFile, File, Depends

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from app_pdf.views.v1.base_logic.pdf_convert_to_image import (
	API_NAME, URL_DATA, get_cloud_run_response,
)
from app_pdf.views.v1.fastapi_views.route import v1_view_pdf_router

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


@v1_view_pdf_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_pdf_convert_to_image(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		file: UploadFile = File(...),
):
	return await get_cloud_run_response(
		token_data=token_data,
		redis_conn=redis_conn,
		file=file
	)
