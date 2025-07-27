import logging
from typing import Literal
from datetime import datetime

from fastapi import UploadFile, File, status, Depends, HTTPException, Query

from core.urls import urls
from schemas.auth import TokenData
from schemas.urls import CloudRunAPIEndpoint
from access_management.api_auth import verify_token
from common.cloud_run import async_request
from common.file_validation import (
	validate_file_type, validate_file_size_mb
)
from common.cost_management import cost_setup, cost_teardown
from common.redis_utils import get_redis_conn
from common.redis_utils import (
	set_user_api_call_lock, release_user_api_call_lock,
)
from app_docs.cloud_run_container_app_docs.v1.utils.view_docs_excel_split import (
	MAX_FILE_SPLIT
)
from app_docs.views.v1.fastapi_views.route import v1_view_docs_router

logger = logging.getLogger(__name__)

APP_NAME, VERSION, API = "app_docs", "v1", "view_docs_excel_split"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]


@v1_view_docs_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_docs_excel_split(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		file: UploadFile = File(...),
		row_count: int = Query(1, ge=1),
		sheet_name: str = Query(None, min_length=1, max_length=31),
		output_format: Literal['xlsx', 'csv'] = Query('xlsx'),
):
	f"""
	Split an Excel file into multiple files based on the number of rows.

	`row_count` is the number of rows to split the Excel file.
	We can split an Excel file in up to {MAX_FILE_SPLIT} files.
	"""
	if not row_count:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Row count must be greater than 0."
		)
	validate_file_type(
		file=file, file_extensions=('xlsx', 'xls'),
		content_type=(URL_DATA.other["media_type"],)
	)

	# Necessary variables
	date_time_now = datetime.now()
	current_date = datetime.now().strftime("%d-%m-%Y")
	timestamp = int(date_time_now.timestamp())

	try:
		# SetUp API call lock
		await set_user_api_call_lock(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
		)

		# Validate file size and extension
		await validate_file_size_mb(
			file=file,
			max_size_mb=URL_DATA.other["file_size_mb"],
		)

		api_cost, is_metered = await cost_setup(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
			current_date=current_date,
		)

		params = {"row_count": row_count, "output_format": output_format}
		if sheet_name:
			params["sheet_name"] = sheet_name

		resp = await async_request(
			url=URL_DATA.url_target,
			method="POST",
			file=file,
			params=params,
		)

		return await cost_teardown(
			api_name=API_NAME,
			redis_conn=redis_conn,
			resp_type="file",
			resp=resp,
			username=token_data.username,
			api_cost=api_cost,
			current_date=current_date,
			timestamp=timestamp,
			is_metered=is_metered,
		)
	except HTTPException as error:

		logging.error(
			f"User {token_data.username} encounter an error when calling "
			f"API: {API_NAME} at "
			f"timestamp: {timestamp}. Response: {error} with status code "
			f"{error.status_code}."
		)

		raise error

	except Exception as error:
		logging.error(
			f"User {token_data.username} encounter an error when calling "
			f"API: {API_NAME} at "
			f"timestamp: {timestamp}. Response: {error} with status code "
			f"{status.HTTP_500_INTERNAL_SERVER_ERROR}."
		)

		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Error processing request. Please try again later.",
		)
	finally:  # Release the API call lock
		await release_user_api_call_lock(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username
		)
