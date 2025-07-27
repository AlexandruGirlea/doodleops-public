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

APP_NAME, VERSION, API = "app_images", "v1", "view_image_watermark_image"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]


@v1_view_images_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_image_watermark_image(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		output_format_type: Literal["jpeg", "png"] = "jpeg",
		grid_rows: int = Query(
			1, title="Number of rows in the watermark grid", ge=1, le=3
		),
		grid_columns: int = Query(
			1, title="Number of columns in the watermark grid", ge=1, le=3
		),
		background_image: UploadFile = File(
			..., description="The image to add the watermark to (PNG, JPG)"
		),
		watermark_image_scale: float = Query(
			0.17, title="Scale factor", ge=0.05, le=1,
			description="Scale factor for the image, between 0.05 and 1"
		),
		watermark_transparency: float = Query(0.5, ge=0, le=1),
		watermark_image: UploadFile = File(
			..., description="The watermark image (PNG, JPG)"
		),
):

	validate_file_type(
		file=background_image, file_extensions=('jpeg', 'jpg', 'png'),
		content_type=tuple(URL_DATA.other["media_type"]),
	)

	validate_file_type(
		file=watermark_image, file_extensions=('jpeg', 'jpg', 'png'),
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
			file=background_image,
			max_size_mb=URL_DATA.other["file_size_mb"],
		)

		await validate_file_size_mb(
			file=watermark_image,
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
				"background_image",
				(
					background_image.filename,
					await background_image.read(),
					background_image.content_type
				)
			),
			(
				"watermark_image",
				(
					watermark_image.filename,
					await watermark_image.read(),
					watermark_image.content_type
				)
			),
		]

		resp = await async_request(
			url=URL_DATA.url_target,
			method="POST",
			override_files=override_files,
			params={
				"output_format_type": output_format_type,
				"grid_rows": grid_rows,
				"grid_columns": grid_columns,
				"watermark_image_scale": watermark_image_scale,
				"watermark_transparency": watermark_transparency,
			},
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
