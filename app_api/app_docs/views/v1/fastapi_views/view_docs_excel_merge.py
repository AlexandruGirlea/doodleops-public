import logging
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
from app_docs.views.v1.fastapi_views.route import v1_view_docs_router

logger = logging.getLogger(__name__)

APP_NAME, VERSION, API = "app_docs", "v1", "view_docs_excel_merge"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]


@v1_view_docs_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_docs_excel_merge(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		files: list[UploadFile] = File(...),
		sheet_name: str = Query(None, min_length=1, max_length=31),
		use_upload_order: bool = Query(False),
):
	"""
	If `use_upload_order` is set to `True`, the order of the uploaded files
	will be used to merge the sheets. Otherwise, the sheets will be merged
	according to the sheet name (alphabetical order).

	If `sheet_name` is provided, only the Excel sheets with the provided
	name will be merged.
	"""
	if len(files) < 2:
		raise HTTPException(
			status_code=400,
			detail="At least two files are required for merging."
		)
	if len(files) > URL_DATA.other["max_number_of_files"]:
		raise HTTPException(
			status_code=400,
			detail=(
				"Maximum number of files allowed is " +
				f"{URL_DATA.other['max_number_of_files']}"
				)
		)

	# check if file names are unique
	if len(files) != len(set([file.filename for file in files])):
		raise HTTPException(
			status_code=400,
			detail="File names must be unique"
		)

	for file in files:
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
		file_sizes = 0

		for f in files:
			contents = await f.read()
			await f.seek(0)
			file_sizes += len(contents)

		if file_sizes > URL_DATA.other["max_files_size_mb"] * 1024 * 1024:
			raise HTTPException(
				status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
				detail=(
					"Files too large. Max size is "
					f"{URL_DATA.other['max_files_size_mb']} MB."
				)
			)

		api_cost, is_metered = await cost_setup(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
			current_date=current_date,
		)

		params = {"use_upload_order": use_upload_order}
		if sheet_name:
			params["sheet_name"] = sheet_name

		resp = await async_request(
			url=URL_DATA.url_target,
			method="POST",
			files=files,
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
