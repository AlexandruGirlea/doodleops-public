import logging

from fastapi import APIRouter
from fastapi import (
	HTTPException, Depends, BackgroundTasks, File, UploadFile, Query
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_file_path, cleanup_temp_dir, read_image_from_file_upload,
)

logger = logging.getLogger(__name__)

image_convert_to_b_w_router = APIRouter(
	tags=["Convert"],
	responses={404: {"description": "Not found"}},
)


@image_convert_to_b_w_router.post(
	urls.get("convert").get("to_b_w"),
	include_in_schema=True,
)
async def to_b_w(
		background_tasks: BackgroundTasks,
		threshold: int = Query(127, ge=0, le=255),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	output_file_path = get_temp_file_path(extension="jpeg")

	img = await read_image_from_file_upload(file=file)

	try:
		gray_image = img.convert("L")
		b_w_image = gray_image.point(
			lambda x: 255 if x > threshold else 0, mode='1'
		)

		b_w_image.save(output_file_path, "JPEG")

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

		return FileResponse(
			output_file_path,
			media_type="image/jpeg",
			filename="b_w_image.jpeg"
		)

	except (OSError, HTTPException, Exception) as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=output_file_path)

		if isinstance(e, HTTPException):
			status_code = e.status_code
			raise HTTPException(
				status_code=status_code,
				detail="Could not convert image to b_w"
			)

		raise HTTPException(
			status_code=500,
			detail="Server error"
		)
