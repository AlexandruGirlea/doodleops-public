import logging
from typing import Literal

from PIL import Image, ImageEnhance
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

image_add_watermark_image_router = APIRouter(
	tags=["Watermark"],
	responses={404: {"description": "Not found"}},
)


@image_add_watermark_image_router.post(
	urls.get("watermark").get("add_image"),
	include_in_schema=True,
)
async def add_watermark_image(
		background_tasks: BackgroundTasks,
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
		token_data: bool = Depends(verify_token),
):
	"""
	An ICO file contains multiple images in different sizes in one file.
	We pass in all ICO_SIZES to create an ICO file with multiple sizes.
	"""
	output_file_path = get_temp_file_path(extension=output_format_type)

	background_image_data = await read_image_from_file_upload(background_image)
	watermark_image_data = await read_image_from_file_upload(watermark_image)

	try:
		background = background_image_data.convert("RGBA")
		watermark = watermark_image_data.convert("RGBA")

		alpha = watermark.split()[3]
		# Adjust brightness to make the watermark semi-transparent
		alpha = ImageEnhance.Brightness(alpha).enhance(watermark_transparency)
		watermark.putalpha(alpha)

		background_width, background_height = background.size
		grid_width = background_width / grid_columns
		grid_height = background_height / grid_rows

		# Maintain watermark aspect ratio while scaling
		watermark_aspect_ratio = watermark.width / watermark.height
		scaled_height = int(grid_height * watermark_image_scale)
		scaled_width = int(scaled_height * watermark_aspect_ratio)

		if scaled_width > grid_width * watermark_image_scale:
			scaled_width = int(grid_width * watermark_image_scale)
			scaled_height = int(scaled_width / watermark_aspect_ratio)

		watermark = watermark.resize(
			(scaled_width, scaled_height), Image.Resampling.LANCZOS
		)

		for row in range(grid_rows):
			for col in range(grid_columns):
				x = col * grid_width + (grid_width - scaled_width) / 2
				y = row * grid_height + (grid_height - scaled_height) / 2
				background.paste(watermark, (int(x), int(y)), watermark)

		if output_format_type == "jpeg":
			background = background.convert("RGB")

		background.save(output_file_path, format=output_format_type.upper())

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
		return FileResponse(
			output_file_path,
			media_type=f"image/{output_format_type}",
			filename=f"watermarked_image.{output_format_type}",
		)

	except (Exception, OSError) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
