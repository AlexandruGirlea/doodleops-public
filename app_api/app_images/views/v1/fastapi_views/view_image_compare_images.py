import logging
from typing import Literal
from datetime import datetime

from fastapi import UploadFile, File, status, Depends, HTTPException, Form

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

APP_NAME, VERSION, API = "app_images", "v1", "view_image_compare_images"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]
CONTOUR_COLORS_MAP = {
	"red": (0, 0, 255),
	"green": (0, 255, 0),
	"blue": (255, 0, 0),
}


@v1_view_images_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_image_compare_images(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		img_1: UploadFile = File(...),
		img_2: UploadFile = File(...),
		contour_color: Literal["read", "green", "blue", "red"] = Form("green"),
):
	for img in {img_1, img_2}:
		validate_file_type(
			file=img, file_extensions=('jpeg', 'jpg', 'png'),
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
		for img in {img_1, img_2}:
			await validate_file_size_mb(
				file=img,
				max_size_mb=URL_DATA.other["file_size_mb"],
			)

		api_cost, is_metered = await cost_setup(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
			current_date=current_date,
		)

		override_files = [
			("img_1", (img_1.filename, await img_1.read(), img_1.content_type)),
			("img_2", (img_2.filename, await img_2.read(), img_2.content_type)),
		]
		resp = await async_request(
				url=URL_DATA.url_target,
				method="POST",
				override_files=override_files,
				data={
					"contour_color": CONTOUR_COLORS_MAP[contour_color],
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
