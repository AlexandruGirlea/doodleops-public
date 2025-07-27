import logging

from fastapi import UploadFile, File, Depends

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from app_pdf.cloud_run_container_app_pdf.v1.schemas.view_pdf_extract_tables import Payload
from app_pdf.views.v1.fastapi_views.route import v1_view_pdf_router
from app_pdf.views.v1.base_logic.pdf_extract_tables import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


@v1_view_pdf_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_pdf_extract_tables(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		file: UploadFile = File(...),
		payload: Payload = Depends(),
):
	return await get_cloud_run_response(
		token_data=token_data,
		redis_conn=redis_conn,
		file=file,
		payload=payload,
	)
