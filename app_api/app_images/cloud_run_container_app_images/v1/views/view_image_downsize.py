import os
import logging
from typing import Literal

from PIL import Image
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

image_downsize_router = APIRouter(
	tags=["Image manipulation"],
	responses={404: {"description": "Not found"}},
)


@image_downsize_router.post(
	urls.get("image_manipulation").get("downsize"),
	include_in_schema=True,
)
async def downsize(
		background_tasks: BackgroundTasks,
		output_format: Literal["jpeg", "jpg", "png"] = Query(
			"jpeg", description="Output format of the image"
		),
		max_height_px: int = Query(
			None, description="Maximum height of the image"
		),
		max_width_px: int = Query(None, description="Maximum width of the image"),
		max_mb_size: float = Query(
			None, description="Maximum file size in MB", gt=0, lt=10
		),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	if not any([max_height_px, max_width_px, max_mb_size]):
		raise HTTPException(
			status_code=400,
			detail=(
				"Please provide at least one of the following: "
				"max_height_px, max_width_px, max_mb_size"
			),
		)

	output_file_path = get_temp_file_path(extension=output_format)
	temp_dir = os.path.dirname(output_file_path)

	image = await read_image_from_file_upload(file)

	if output_format in ('jpeg', 'jpg') and image.mode in ('RGBA', 'LA'):
		image = image.convert('RGB')
	try:
		if max_height_px or max_width_px:
			if max_height_px and max_width_px:
				ratio = min(
					max_width_px / image.width, max_height_px / image.height
				)
				new_size = (int(image.width * ratio), int(image.height * ratio))
			elif max_height_px:
				ratio = max_height_px / image.height
				new_size = (int(image.width * ratio), max_height_px)
			else:  # max_width_px
				ratio = max_width_px / image.width
				new_size = (max_width_px, int(image.height * ratio))

			image = image.resize(new_size, Image.Resampling.LANCZOS)

			image.save(output_file_path, format=output_format)

		else:  # max_mb_size
			max_size_bytes = max_mb_size * 1024 * 1024

			if output_format.lower() == 'png':
				width, height = image.size
				min_scale = 0.1  # Minimum scale factor (10% of original size)
				max_scale = 1.0  # Maximum scale factor (100% of original size)
				tolerance = 0.01  # Tolerance for binary search
				max_iterations = 20  # Prevent infinite loops

				best_scale = None
				best_image = None
				resized_image = None

				iteration = 0
				while min_scale <= max_scale and iteration < max_iterations:
					iteration += 1
					scale = (min_scale + max_scale) / 2
					new_size = (
						max(1, int(width * scale)), max(1, int(height * scale))
					)

					# Resize the image
					resized_image = image.resize(
						new_size, Image.Resampling.LANCZOS
					)

					temp_file_path = os.path.join(temp_dir, "temp_resized.png")
					resized_image.save(
						temp_file_path, format='PNG', compress_level=9
					)

					size = os.path.getsize(temp_file_path)

					if size <= max_size_bytes:
						best_scale = scale
						best_image = resized_image.copy()  # Store a copy of the acceptable image
						min_scale = scale + tolerance  # Try to find a larger scale
					else:
						max_scale = scale - tolerance  # Scale down

					if max_scale - min_scale < tolerance:
						break

				if best_image:
					# Save the best acceptable image
					best_image.save(
						output_file_path, format='PNG', compress_level=9)

				elif resized_image:
					resized_image.save(
						output_file_path, format='PNG', compress_level=9
					)

			else:
				param_name = 'quality'

				temp_file_path = output_file_path
				low, high = 1, 100  # quality ranges from 1 to 100
				while low <= high:
					mid = (low + high) // 2

					temp_file_path = os.path.join(
						temp_dir, f"temp_{mid}.{output_format}"
					)
					image.save(
						temp_file_path, format=output_format, **{param_name: mid}
					)
					size = os.path.getsize(temp_file_path)  # in bytes
					if size <= max_size_bytes:
						low = mid + 1
					else:
						high = mid - 1

				output_file_path = temp_file_path

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
		return FileResponse(
			output_file_path, media_type=f"image/{output_format.lower()}",
			filename=f"downsized_image.{output_format.lower()}"
		)

	except (Exception, OSError) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
