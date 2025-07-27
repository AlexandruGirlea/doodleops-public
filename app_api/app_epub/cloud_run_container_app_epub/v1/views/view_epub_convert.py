"""
This can convert different formats

- PDF to epub
- epub to PDF
- word to epub
- epub to word

ex: ebook-convert test.epub test.docx
"""
import os
import logging
import subprocess
from typing import Literal

from fastapi.responses import FileResponse
from fastapi import (
	APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends,
)

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import get_unique_temp_dir, cleanup_temp_dir

logger = logging.getLogger(__name__)

file_convert_router = APIRouter(
	tags=["File Convert API"],
	responses={404: {"description": "Not found"}},
)

# input and output formats
allowed_combinations = {
	'.pdf': {'epub', },
	'.epub': {'pdf', 'docx'},
	'.docx': {'epub', },
}


@file_convert_router.post(
	urls.get("convert_format").get("convert"),
	include_in_schema=True,
)
async def convert_file(
		background_tasks: BackgroundTasks,
		output_format: Literal['pdf', 'epub', 'docx'] = Form(...),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	if file.filename == '':
		raise HTTPException(status_code=400, detail="No selected file")

	# get file extensions
	input_extension = os.path.splitext(file.filename)[-1].lower()

	if input_extension not in allowed_combinations.keys():
		raise HTTPException(status_code=400, detail="Unsupported input file type")

	if output_format not in allowed_combinations[input_extension]:
		raise HTTPException(
			status_code=400, detail="Unsupported output file type"
		)

	temp_dir = get_unique_temp_dir()
	if not os.path.exists(temp_dir):
		os.makedirs(temp_dir, exist_ok=False)
	else:
		logging.error(f"Temporary directory already exists, {temp_dir}")
		raise HTTPException(
			status_code=500, detail="Temporary directory already exists")

	try:
		input_file_path = os.path.join(temp_dir, f'input{input_extension}')
		output_file_path = os.path.join(temp_dir, f'output.{output_format}')

		with open(input_file_path, "wb") as f:
			f.write(await file.read())

		# Convert file using ebook-convert
		result = subprocess.run(
			['ebook-convert', input_file_path, output_file_path],
			capture_output=True,
		)

		if result.returncode != 0:
			raise HTTPException(status_code=500, detail="Conversion failed")

		background_tasks.add_task(cleanup_temp_dir, temp_dir)
		return FileResponse(
			output_file_path,
			filename=f'output.{output_format}',
		)

	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(temp_dir)
		raise HTTPException(status_code=500, detail=str(e))
