import os
import logging
import subprocess

import cairosvg
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
from utils.constants import CONVERT_MATRIX


logger = logging.getLogger(__name__)

image_convert_format_router = APIRouter(
	tags=["Convert"],
	responses={404: {"description": "Not found"}},
)

CONVERT_ERROR = "Error converting image"


@image_convert_format_router.post(
	urls.get("convert").get("format"),
	include_in_schema=True,
)
async def convert_format(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(...),
		output_img_format: str = Query(..., min_length=3, max_length=4),
		token_data: bool = Depends(verify_token),
):
	output_img_format = output_img_format.lower()

	if output_img_format in {"jpeg", "jpg", "jpe"}:
		pillow_format = "jpeg"
	elif output_img_format in {"tiff", "tif"}:
		pillow_format = "tiff"
	elif output_img_format in {"bmp", "dib"}:
		pillow_format = "bmp"
	else:
		pillow_format = output_img_format

	input_file_name = file.filename
	input_file_extension = input_file_name.split(".")[-1].lower()

	if output_img_format == input_file_extension:
		raise HTTPException(
			status_code=400,
			detail="Output format is the same as input format"
		)

	supported_input_file_extensions = (
			CONVERT_MATRIX.get("pillow").keys() |
			CONVERT_MATRIX.get("imagemagick").keys() |
			CONVERT_MATRIX.get("cairosvg").keys()
	)

	if input_file_extension not in supported_input_file_extensions:
		raise HTTPException(status_code=400, detail="Unsupported input file type")
	elif not any(
		output_img_format in CONVERT_MATRIX[k].get(input_file_extension, set())
		for k in CONVERT_MATRIX
	):
		raise HTTPException(
			status_code=400, detail="Unsupported output file type"
		)

	output_file_path = get_temp_file_path(extension=output_img_format)
	temp_dir = os.path.dirname(output_file_path)

	if input_file_extension in CONVERT_MATRIX.get("pillow"):
		image = await read_image_from_file_upload(file)

		if image.mode == "RGBA":
			image = image.convert("RGB")

		image.save(output_file_path, format=pillow_format.upper())

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)
		return FileResponse(
			output_file_path,
			media_type=f"image/{output_img_format}",
			filename=f"converted_image.{output_img_format}"
		)
	elif input_file_extension in CONVERT_MATRIX.get("cairosvg"):
		svg_path = os.path.join(temp_dir, input_file_name)
		with open(svg_path, "wb") as f:
			f.write(await file.read())

		cairosvg.svg2png(url=svg_path, write_to=output_file_path)
		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

		return FileResponse(
			output_file_path,
			media_type=f"image/{output_img_format}",
			filename=f"converted_image.{output_img_format}"
		)

	try:  # input_file_extension is in CONVERT_MATRIX.get("imagemagick")
		file_path = os.path.join(temp_dir, input_file_name)
		with open(file_path, "wb") as f:
			f.write(await file.read())

		command = [
			"convert",
			file_path,
			output_file_path
		]

		result = subprocess.run(command, capture_output=True, text=True)

		if result.returncode != 0:
			raise HTTPException(
				status_code=400,
				detail=CONVERT_ERROR
			)

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

		return FileResponse(
			output_file_path,
			media_type=f"image/{output_img_format}",
			filename=f"converted_image.{output_img_format}"
		)

	except (OSError, HTTPException, Exception) as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=output_file_path)

		if isinstance(e, HTTPException):
			status_code = e.status_code
			raise HTTPException(
				status_code=status_code,
				detail=CONVERT_ERROR
			)

		raise HTTPException(
			status_code=500,
			detail="Server error"
		)
