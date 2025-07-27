import subprocess
import logging
from io import BytesIO
from typing import Literal

import cv2
import cairosvg
import numpy as np
from pyzbar.pyzbar import decode, Decoded
from PIL import Image
from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi import (
	HTTPException, Depends, Form, UploadFile, BackgroundTasks, File
)

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_file_path, read_image_from_file_upload, cleanup_temp_dir,
	overlay_png_on_svg
)

ERROR_CORRECT_LEVELS = {
	"7": "L",
	"15": "M",
	"25": "Q",
	"30": "H"
}

logger = logging.getLogger(__name__)

image_create_qr_code_router = APIRouter(
	tags=["QR & Bar Codes"],
	responses={404: {"description": "Not found"}},
)


def validate_qr_image(image_path: str) -> str:
	try:
		with Image.open(image_path) as i:
			data = decode(i)
		if data and isinstance(data, list):
			if isinstance(data[0], Decoded):
				return data[0].data.decode("utf-8")

		img = cv2.imread(image_path)
		detector = cv2.QRCodeDetector()
		data, vertices_array, _ = detector.detectAndDecode(img)
		del img, detector
		if data:
			return data

	except Exception as e:
		logging.error(f"Error: {e}")
		raise ValueError("Invalid QR code image, please provide a valid image.")


def validate_qr_image_svg(image_path: str) -> str:
	try:
		# Convert SVG to PNG in memory
		with open(image_path, "rb") as svg_file:
			svg_data = svg_file.read()
			png_data = cairosvg.svg2png(bytestring=svg_data)

		# Load the PNG data into an image object
		with Image.open(BytesIO(png_data)) as img:
			# Decode the image using pyzbar
			decoded_data = decode(img)
			if decoded_data:
				return decoded_data[0].data.decode("utf-8")

			img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
			detector = cv2.QRCodeDetector()
			data, vertices_array, _ = detector.detectAndDecode(img_cv)

			if data:
				return data

	except Exception as e:
		logging.error(f"Error decoding SVG: {e}")
		raise ValueError("Invalid QR code SVG image, please provide a valid image.")


@image_create_qr_code_router.post(
	urls.get("read_codes").get("create_qr_code"),
	include_in_schema=True,
	response_class=FileResponse,
	responses={
		200: {
			"description": "Returns an PNG file containing the QR code.",
		}}
)
async def create_png_qr_code(
		background_tasks: BackgroundTasks,
		text: str = Form(...),
		scale: int = Form(10, ge=1, le=50),
		output_format: Literal["PNG", "SVG"] = Form("PNG"),
		fill_color: str = Form(
			"000000", description="Ex=`000000`, we use Hex Color"
		),
		background_color: str = Form(
			"FFFFFF",
			description="Ex=`FFFFFF`, we use Hex Color"
		),
			error_correction_level: Literal["7", "15", "25", "30"] = Form(
			15,
			description="Error correction level in %, in case of QR code damage."
		),
		file: UploadFile = File(
			None, description="embed a PNG logo into the QR code"
		),
		token_data: bool = Depends(verify_token),
) -> FileResponse:
	"""
	Create a QR code from text in PNG format.\n
	Optional:\n
	- Control the color of the QR code\n
	- Error correction level in %, in case of QR code damage\n
	- Insert a PNG logo into the QR code

	OBS: if file provided, then error_correction_level is ignored.
	"""
	qr_file_path = get_temp_file_path(extension=output_format.lower())

	if not text or len(text) > 1000:
		raise HTTPException(
			status_code=400,
			detail="Text must be provided and should not exceed 1000 characters."
		)

	png_file_content = None
	if file:
		if file.filename.split(".")[-1].lower() != "png":
			raise HTTPException(
				status_code=400,
				detail="Unsupported file type, please provide a PNG file."
			)
		png_file_content = await read_image_from_file_upload(file)

	command = [
		"qrencode",
		"-o", qr_file_path,
		"-t", output_format,
		"-l", "H" if file else ERROR_CORRECT_LEVELS[error_correction_level],
		"--foreground", fill_color,
		"--background", background_color,
		text
	]

	if output_format == "PNG":
		command.insert(5, "-s")
		command.insert(6, str(scale))

	try:
		# Run the command
		result = subprocess.run(command, capture_output=True, text=True)

		if result.returncode != 0:
			print("Error generating QR code:", result.stderr)
			raise HTTPException(
				status_code=500,
				detail="QR code creation failed, please try again later."
			)

		if png_file_content and output_format == "PNG":
			with Image.open(qr_file_path) as qr_image:
				if qr_image.mode != 'RGB':
					qr_image = qr_image.convert('RGBA')

				basewidth = qr_image.size[0] // 5
				wpercent = (basewidth / float(png_file_content.size[0]))
				hsize = int((float(png_file_content.size[1]) * wpercent))
				logo = png_file_content.resize(
					(basewidth, hsize), Image.Resampling.LANCZOS
				)

				# Calculate the position to place the logo (centered)
				x = (qr_image.size[0] - logo.size[0]) // 2
				y = (qr_image.size[1] - logo.size[1]) // 2

				# Paste the logo onto the QR code
				qr_image.paste(
					logo,
					(x, y),
					mask=logo if logo.mode == 'RGBA' else None
				)

				qr_image.save(qr_file_path)

		elif png_file_content and output_format == "SVG":
			overlay_png_on_svg(
				svg_path=qr_file_path,
				png_file_content=png_file_content,
				output_path=qr_file_path
			)

		if output_format == "PNG":
			qr_data = validate_qr_image(qr_file_path)
		else:  # SVG
			qr_data = validate_qr_image_svg(qr_file_path)

		if not qr_data or qr_data != text:
			raise HTTPException(
				status_code=500,
				detail="QR code creation failed, please try again."
			)

		background_tasks.add_task(cleanup_temp_dir, file_path=qr_file_path)
		return FileResponse(
			qr_file_path, media_type="image/png",
			filename=f"qr_code.{output_format.lower()}"
		)

	except (OSError, HTTPException, Exception) as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=qr_file_path)
		status_code = 500
		if isinstance(e, HTTPException):
			status_code = e.status_code
		raise HTTPException(
				status_code=status_code,
				detail="QR code creation failed, please try again later."
			)
