import logging

from rembg import remove
from fastapi import APIRouter
from fastapi import HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_file_path, cleanup_temp_dir, read_image_from_file_upload
)

logger = logging.getLogger(__name__)

image_remove_background_router = APIRouter(
	tags=["Image manipulation"],
	responses={404: {"description": "Not found"}},
)


@image_remove_background_router.post(
	urls.get("image_manipulation").get("remove_background"),
	include_in_schema=True,
)
async def remove_background(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	output_file_path = get_temp_file_path(extension="png")

	image = await read_image_from_file_upload(file)

	try:
		output = remove(image)
		output.save(output_file_path)
		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

		return FileResponse(
			output_file_path,
			media_type="image/png",
			filename="output.png",
		)

	except (Exception, OSError) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
