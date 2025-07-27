import logging
from datetime import datetime

from fastapi import UploadFile, File, status, Depends, HTTPException

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
from app_docs.views.v1.fastapi_views.route import v1_view_docs_router

logger = logging.getLogger(__name__)

APP_NAME, VERSION, API = "app_docs", "v1", "view_docs_excel_remove_empty_rows"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]


@v1_view_docs_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_docs_excel_remove_empty_rows(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		file: UploadFile = File(...),
):
	"""
	Removes rows that are completely empty from an Excel file.
	"""
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

		resp = await async_request(
			url=URL_DATA.url_target,
			method="POST",
			file=file,
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

		logger.error(
			f"User {token_data.username} encounter an error when calling "
			f"API: {API_NAME}, target: {URL_DATA.url_target} at "
			f"timestamp: {timestamp}. Response: {error} with status code "
			f"{error.status_code}."
		)

		raise error

	except Exception as error:
		logger.error(
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
