import logging
from typing import Literal

from fastapi import APIRouter
from fastapi import (
	HTTPException, Depends, BackgroundTasks, File, UploadFile, Query
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_file_path, cleanup_temp_dir, read_image_from_file_upload
)

logger = logging.getLogger(__name__)

image_create_thumbnail_router = APIRouter(
	tags=["Create"],
	responses={404: {"description": "Not found"}},
)


@image_create_thumbnail_router.post(
	urls.get("create").get("thumbnail"),
	include_in_schema=True,
)
async def create_thumbnail(
		background_tasks: BackgroundTasks,
		output_format_type: Literal["jpeg", "png", "webp"] = "jpeg",
		width: int = Query(128, ge=1, le=1024),
		height: int = Query(128, ge=1, le=1024),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	output_file_path = get_temp_file_path(extension=output_format_type)

	image = await read_image_from_file_upload(file)

	if image.mode == "RGBA":
		image = image.convert("RGB")

	try:
		image.thumbnail((width, height))
		image.save(output_file_path, format=output_format_type.upper())
		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
		return FileResponse(
			output_file_path,
			media_type=f"image/{output_format_type}",
			filename=f"thumbnail.{output_format_type}",
		)

	except (Exception, OSError) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
