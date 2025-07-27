import logging
from datetime import datetime

import redis.asyncio as redis
from fastapi import UploadFile, status, HTTPException

from core.urls import urls
from core.settings import GENERIC_ERROR_MSG
from schemas.auth import TokenData
from schemas.urls import CloudRunAPIEndpoint
from common.cloud_run import async_request
from common.file_validation import validate_file_type, validate_file_size_mb
from common.cost_management import cost_setup, cost_teardown
from common.redis_utils import set_user_api_call_lock, release_user_api_call_lock


APP_NAME, VERSION, API = "app_pdf", "v1", "view_pdf_insert_pdf"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]

logger = logging.getLogger("APP_API_"+API_NAME+__name__)


async def get_cloud_run_response(
		token_data: TokenData, redis_conn: redis.Redis, base_file: UploadFile,
		insert_file: UploadFile, after_page_number: int
):
	if after_page_number and after_page_number < 0:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Page number out of range"
		)

	validate_file_type(
		file=base_file, file_extensions=('pdf',),
		content_type=tuple(URL_DATA.other["media_type"]),
	)
	validate_file_type(
		file=insert_file, file_extensions=('pdf',),
		content_type=tuple(URL_DATA.other["media_type"]),
	)

	date_time_now = datetime.now()
	current_date = datetime.now().strftime("%d-%m-%Y")
	timestamp = int(date_time_now.timestamp())

	try:
		await set_user_api_call_lock(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
		)

		await validate_file_size_mb(
			file=base_file,
			max_size_mb=URL_DATA.other["file_size_mb"],
		)
		await validate_file_size_mb(
			file=insert_file,
			max_size_mb=URL_DATA.other["file_size_mb"],
		)

		api_cost, is_metered = await cost_setup(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
			current_date=current_date,
		)
		override_files = [
			(
				"base_file",
				(
					base_file.filename, await base_file.read(),
					base_file.content_type
				)
			),
			(
				"insert_file",
				(
					insert_file.filename, await insert_file.read(),
					insert_file.content_type
				)
			),
		]

		resp = await async_request(
			url=URL_DATA.url_target,
			method="POST",
			override_files=override_files,
			params=(
				{"after_page_number": after_page_number}
				if after_page_number is not None else after_page_number
			),
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
			f"API: {API_NAME} at timestamp: {timestamp}. Response: {error}."
		)

		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=GENERIC_ERROR_MSG
		)
	finally:  # Release the API call lock
		await release_user_api_call_lock(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username
		)
