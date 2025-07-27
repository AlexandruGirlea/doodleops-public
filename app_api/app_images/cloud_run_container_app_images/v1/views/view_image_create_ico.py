import logging

from fastapi import APIRouter
from fastapi import HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_file_path, cleanup_temp_dir, read_image_from_file_upload
)

logger = logging.getLogger(__name__)

image_create_ico_router = APIRouter(
	tags=["Create"],
	responses={404: {"description": "Not found"}},
)

ICO_SIZES = [16, 32, 64, 128]


@image_create_ico_router.post(
	urls.get("create").get("ico"),
	include_in_schema=True,
)
async def create_ico(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	"""
	An ICO file contains multiple images in different sizes in one file.
	We pass in all ICO_SIZES to create an ICO file with multiple sizes.
	"""
	output_file_path = get_temp_file_path(extension="ico")

	img = await read_image_from_file_upload(file)

	try:
		img.convert("RGBA")
		icon_sizes = [(size, size) for size in ICO_SIZES]
		img.save(output_file_path, format='ICO', sizes=icon_sizes)

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
		return FileResponse(
			output_file_path,
			media_type="image/x-icon",
			filename="favicon.ico"
		)

	except (Exception, OSError) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
