"""Not working yet. Maybe use AI."""

import logging
from datetime import datetime

from fastapi.responses import JSONResponse
from fastapi import status, Depends, HTTPException, Form

from core.urls import urls
from core.settings import GENERIC_ERROR_MSG
from schemas.auth import TokenData
from schemas.urls import CloudRunAPIEndpoint
from access_management.api_auth import verify_token
from common.cloud_run import async_request
from common.cost_management import cost_setup, cost_teardown
from common.redis_utils import get_redis_conn
from common.redis_utils import set_user_api_call_lock, release_user_api_call_lock
from app_images.views.v1.fastapi_views.route import v1_view_images_router

logger = logging.getLogger(__name__)

APP_NAME, VERSION, API = "app_images", "v1", "view_image_create_barcode"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]

MAX_LENGTH = 1000

CODE_TYPES = {
	'codabar': 20,
	'code128': 48,
	'code39': 25,
	'ean': 13,
	'ean13': 13,
	'ean13-guard': 13,
	'ean14': 14,
	'ean8': 8,
	'ean8-guard': 8,
	'gs1': None,
	'gs1_128': None,
	'gtin': 14,
	'isbn': 13,
	'isbn10': 10,
	'isbn13': 13,
	'issn': 8,
	'itf': None,
	'jan': 13,
	'nw-7': 20,
	'pzn': 8,
	'upc': 12,
	'upca': 12,
}


@v1_view_images_router.get(URL_DATA.api_url, include_in_schema=True)
async def view_image_create_barcode_get(
	token_data: TokenData = Depends(verify_token),
):
	ordered_code_types = sorted(CODE_TYPES.keys())
	ordered_code_types.remove("code128")
	ordered_code_types.insert(0, "code128")
	return JSONResponse(
		content={"code_types": ordered_code_types},
	)


@v1_view_images_router.post(URL_DATA.api_url, include_in_schema=True)
async def view_image_create_barcode(
		token_data: TokenData = Depends(verify_token),
		redis_conn=Depends(get_redis_conn),
		text: str = Form(...),
		code_type: str = Form("code128"),

):
	if code_type not in CODE_TYPES.keys():
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Invalid barcode type."
		)
	if CODE_TYPES[code_type] and len(text) > CODE_TYPES[code_type]:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=f"Text too long for {code_type}."
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

		api_cost, is_metered = await cost_setup(
			api_name=API_NAME,
			redis_conn=redis_conn,
			username=token_data.username,
			current_date=current_date,
		)

		resp = await async_request(
			url=URL_DATA.url_target,
			method="POST",
			json={
				"text": text,
				"code_type": code_type,
			}
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
