"""
In GCP Cloud we need to enable the Google Drive API
https://console.cloud.google.com/apis/api/drive.googleapis.com/metrics
"""
import logging

from fastapi import UploadFile, File, BackgroundTasks, Depends

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.other import cleanup_temp_dir
from common.redis_utils import get_redis_conn
from app_pdf.views.v1.base_logic.pdf_convert_to_word_pro import (
	URL_DATA, get_response,
)
from app_pdf.views.v1.fastapi_views.route import v1_view_pdf_router

logger = logging.getLogger(__name__)


@v1_view_pdf_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_pdf_convert_to_word_pro(
		background_tasks: BackgroundTasks,
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		file: UploadFile = File(...)
):
	resp = await get_response(
		token_data=token_data,
		redis_conn=redis_conn,
		file=file,
	)
	background_tasks.add_task(cleanup_temp_dir, resp["temp_dir"])
	return resp["resp"]
