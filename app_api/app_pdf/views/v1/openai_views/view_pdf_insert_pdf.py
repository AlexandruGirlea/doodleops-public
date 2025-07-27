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
from app_pdf.views.v1.base_logic.pdf_insert_pdf import (
	API_NAME, URL_DATA, get_cloud_run_response,
)

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


@v1_view_pdf_router_openai.post(
	f"{URL_DATA.api_url}/openai",
	include_in_schema=True,
	description=(
			"Accepts exactly 2 PDF files as openaiFileIdRefs. IMPORTANT: 1st is "
			"Base PDF (destination), 2nd is Insert PDF (source). Make sure you "
			"follow this strict order. Optionally, provide a page number after "
			"which to insert the new PDF."
	),
	summary=(
			"Insert PDF into another PDF. Always require explicit specification "
			"of Destination and Insert PDFs."
	),
)
async def view_pdf_insert_pdf_openai(
		request: Request,
		RequestModel: RequestModel,
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		after_page_number: int = Query(
			None,
			description=(
					"Optional parameter to specify the page number after which "
					"to insert the PDF"
			)
		)
) -> ResponseModel:
	files = await get_file_from_request(
		request=request,
		api_name=API_NAME,
		username=token_data.username,
		max_no_of_files=2,
		min_no_of_files=2,
	)
	base_file = files[0]
	insert_file = files[-1]

	resp = await get_cloud_run_response(
		token_data=token_data,
		redis_conn=redis_conn,
		after_page_number=after_page_number,
		base_file=base_file,
		insert_file=insert_file,
	)

	del base_file
	del insert_file
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
