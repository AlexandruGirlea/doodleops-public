import logging
from typing import Literal
from datetime import datetime

from fastapi import UploadFile, File, status, Depends, HTTPException, Query

from core.urls import urls
from core.settings import GENERIC_ERROR_MSG
from schemas.auth import TokenData
from schemas.urls import CloudRunAPIEndpoint
from access_management.api_auth import verify_token
from common.cloud_run import async_request
from common.file_validation import validate_file_type, validate_file_size_mb
from common.cost_management import cost_setup, cost_teardown
from common.redis_utils import get_redis_conn
from common.redis_utils import set_user_api_call_lock, release_user_api_call_lock
from app_images.views.v1.fastapi_views.route import v1_view_images_router

logger = logging.getLogger(__name__)

APP_NAME, VERSION, API = "app_images", "v1", "view_image_downsize"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]


@v1_view_images_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_image_downsize(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		output_format: Literal["jpeg", "png"] = Query(
			"jpeg", description="Output format of the image"
		),
		max_height_px: int = Query(
			None, description="Maximum height of the image"
		),
		max_width_px: int = Query(None, description="Maximum width of the image"),
		max_mb_size: float = Query(
			None, description="Maximum file size in MB", gt=0, lt=10
		),
		file: UploadFile = File(...),
):
	if not any([max_height_px, max_width_px, max_mb_size]):
		raise HTTPException(
			status_code=400,
			detail=(
				"Please provide at least one of the following: "
				"max height, max width, or max file size."
			),
		)

	validate_file_type(
		file=file, file_extensions=('jpeg', 'jpg', 'png'),
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
			file=file,
			max_size_mb=URL_DATA.other["file_size_mb"],
		)

		api_cost, is_metered = await cost_setup(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
			current_date=current_date,
		)

		params = {"output_format": output_format}

		if max_height_px:
			params["max_height_px"] = max_height_px
		if max_width_px:
			params["max_width_px"] = max_width_px
		if max_mb_size:
			params["max_mb_size"] = max_mb_size

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
