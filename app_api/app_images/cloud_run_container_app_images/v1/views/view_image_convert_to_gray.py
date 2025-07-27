import logging

from fastapi import APIRouter
from fastapi import HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_file_path, cleanup_temp_dir, read_image_from_file_upload,
)

logger = logging.getLogger(__name__)

image_convert_to_gray_router = APIRouter(
	tags=["Convert"],
	responses={404: {"description": "Not found"}},
)


@image_convert_to_gray_router.post(
	urls.get("convert").get("to_gray"),
	include_in_schema=True,
)
async def to_gray(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	output_file_path = get_temp_file_path(extension="jpeg")

	img = await read_image_from_file_upload(file=file)

	try:
		gray_image = img.convert("L")
		gray_image.save(output_file_path, "JPEG")

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

		return FileResponse(
			output_file_path,
			media_type="image/jpeg",
			filename="gray_image.jpeg"
		)

	except (OSError, HTTPException, Exception) as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=output_file_path)

		if isinstance(e, HTTPException):
			status_code = e.status_code
			raise HTTPException(
				status_code=status_code,
				detail="Could not convert image to gray"
			)

		raise HTTPException(
			status_code=500,
			detail="Server error"
		)
