import os
import logging
from typing import Literal
from urllib.parse import unquote

from PIL import ImageDraw, ImageFont, Image
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

image_add_watermark_text_router = APIRouter(
	tags=["Watermark"],
	responses={404: {"description": "Not found"}},
)

MAX_TEXT_LENGTH = 25
DEFAULT_FONT_PATH = "/app_images/utils/Roboto-Medium.ttf"


@image_add_watermark_text_router.post(
	urls.get("watermark").get("add_text"),
	include_in_schema=True,
)
async def add_watermark_text(
		background_tasks: BackgroundTasks,
		text: str = Query(
			...,
			title=f"Text to be used as watermark, max length {MAX_TEXT_LENGTH}",
		),
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
		font_file: UploadFile = File(
			None, description="The font file to use for the text"
		),
		font_scale: float = Query(
			0.05, title="Scale factor", ge=0.01, le=0.1,
			description=(
					"Scale factor for the font, between 0.01 and 0.1 "
					"relative to the image size"
			),
		),
		rgb_text_color: str = Query(
			"255,255,255", title="RGB text color",
			description="RGB color for the text in the format '255,255,255'"
		),
		transparency: float = Query(0.5, ge=0, le=1),
		rotation_angle: int = Query(0, ge=-360, le=360),
		token_data: bool = Depends(verify_token),
):
	"""
	OBS: How readable the text is depends on the resolution of the base image.
	"""

	text = unquote(text)
	if len(text) > MAX_TEXT_LENGTH:
		raise HTTPException(
			status_code=400,
			detail=f"Text length exceeds the maximum limit of {MAX_TEXT_LENGTH}"
		)

	if rgb_text_color:
		colors = [
			int(color) for color in rgb_text_color.split(",")
			if color.isdigit() and 0 <= int(color) <= 255
		]
		if len(colors) != 3:
			raise HTTPException(
				status_code=400,
				detail="RGB color values must be between 0 and 255"
			)
	else:
		colors = [255, 255, 255]

	transparency = int(255 * transparency)

	output_file_path = get_temp_file_path(extension=output_format_type)
	temp_dir = os.path.dirname(output_file_path)

	background_image_data = await read_image_from_file_upload(background_image)

	font_path = DEFAULT_FONT_PATH
	if font_file:
		if not font_file.filename.endswith(".ttf"):
			raise HTTPException(
				status_code=400,
				detail="Font file must be a TrueType font (.ttf)"
			)
		font_path = os.path.join(temp_dir, "font.ttf")
		with open(font_path, "wb") as font:
			font.write(await font_file.read())

	try:

		background = background_image_data.convert("RGBA")

		# Calculate font size based on image dimensions and scale
		font_size = int(font_scale * background.height)
		font = ImageFont.truetype(font_path, font_size)

		# Calculate text placement based on grid settings
		grid_width = background.width / grid_columns
		grid_height = background.height / grid_rows

		for row in range(grid_rows):
			for col in range(grid_columns):
				# Create text image for each grid cell
				text_img = Image.new(
					'RGBA', (int(grid_width), int(grid_height)),
					tuple([*colors, 0])
				)
				text_draw = ImageDraw.Draw(text_img)
				text_width, text_height = text_draw.textbbox(
					(0, 0), text, font=font
				)[2:]
				text_position = (
					(grid_width - text_width) / 2, (grid_height - text_height) / 2
				)
				text_draw.text(
					text_position, text, font=font,
					fill=tuple([*colors, transparency])
				)

				# Rotate the text image
				text_img = text_img.rotate(rotation_angle, expand=1)

				# Calculate the exact position to place the text image in the grid cell
				x = col * grid_width + (grid_width - text_img.width) / 2
				y = row * grid_height + (grid_height - text_img.height) / 2

				# Paste the rotated text with transparency
				background.paste(text_img, (int(x), int(y)), text_img)

		if output_format_type == "jpeg":
			background = background.convert("RGB")

		background.save(output_file_path, format=output_format_type)

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
