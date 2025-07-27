import logging
from typing import List
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

APP_NAME, VERSION, API = "app_images", "v1", "view_image_create_gif"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]

MAX_NUM_IMAGES = 40


@v1_view_images_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_image_create_gif(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		loop: int = Query(
			0, ge=0, le=100, description="Number of loops for the GIF"
		),
		duration: int = Query(
			200, ge=50, le=1000,
			description="Duration of each frame in milliseconds"
		),
		img_files: List[UploadFile] = File(None),
		movie_file: UploadFile = File(None),
):
	if not img_files and not movie_file:
		raise HTTPException(status_code=400, detail="No files provided")
	elif movie_file and img_files:
		raise HTTPException(
			status_code=400,
			detail="Either provide multiple images or a movie file"
		)
	if img_files:
		number_of_images = len(img_files)
		if number_of_images > MAX_NUM_IMAGES:
			raise HTTPException(
				status_code=400,
				detail=(
					"Number of images exceeds the maximum limit of "
					f"{MAX_NUM_IMAGES}."
				)
			)
		for img in img_files:
			validate_file_type(
				file=img, file_extensions=('jpeg', 'jpg', 'png'),
				content_type=tuple(URL_DATA.other["media_type"]),
			)
	else:
		validate_file_type(
			file=movie_file, file_extensions=('mp4', 'avi', 'mov'),
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

		if img_files:
			# URL_DATA.other["file_size_mb"] / MAX_NUM_IMAGES rounded to 2 decimal
			max_img_file_size_mb = round(
				URL_DATA.other.get("file_size_mb", 10) / number_of_images, 2
			)
			try:
				for img in img_files:
					await validate_file_size_mb(
						file=img,
						max_size_mb=max_img_file_size_mb,
					)
			except HTTPException:
				raise HTTPException(
					status_code=400,
					detail=(
						f"Total size of images exceeds the maximum limit of "
						f"{URL_DATA.other['file_size_mb']} MB."
					)
				)
		else:
			await validate_file_size_mb(
				file=movie_file,
				max_size_mb=URL_DATA.other["file_size_mb"],
			)

		api_cost, is_metered = await cost_setup(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
			current_date=current_date,
		)

		if img_files:
			# img_files is a list of UploadFile objects
			override_files = [
				(
					"img_files",
					(img.filename, await img.read(), img.content_type)
				)
				for img in img_files
			]
		else:
			# movie_file is an UploadFile object
			override_files = [
				(
					"movie_file",
					(
						movie_file.filename, await movie_file.read(),
						movie_file.content_type
					)
				)
			]

		resp = await async_request(
			url=URL_DATA.url_target,
			method="POST",
			override_files=override_files,
			params={
				"loop": loop,
				"duration": duration,
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
