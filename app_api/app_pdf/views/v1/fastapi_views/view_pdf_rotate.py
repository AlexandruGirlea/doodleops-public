import logging

from fastapi import UploadFile, File, Depends, Form

from schemas.auth import TokenData
from access_management.api_auth import verify_token
from common.redis_utils import get_redis_conn
from app_pdf.views.v1.fastapi_views.route import v1_view_pdf_router
from app_pdf.views.v1.base_logic.pdf_rotate import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


@v1_view_pdf_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_pdf_rotate(
		pages_to_rotate_right: str = Form(
			None, title="Pages to rotate right",
			description="Comma separated page numbers"
		),
		pages_to_rotate_left: str = Form(
			None, title="Pages to rotate left",
			description="Comma separated page numbers"
		),
		pages_to_rotate_upside_down: str = Form(
			None, title="Pages to rotate upside down",
			description="Comma separated page numbers"
		),
		file: UploadFile = File(...),
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
):
	return await get_cloud_run_response(
		token_data=token_data,
		redis_conn=redis_conn,
		file=file,
		pages_to_rotate_right=pages_to_rotate_right,
		pages_to_rotate_left=pages_to_rotate_left,
		pages_to_rotate_upside_down=pages_to_rotate_upside_down
	)
