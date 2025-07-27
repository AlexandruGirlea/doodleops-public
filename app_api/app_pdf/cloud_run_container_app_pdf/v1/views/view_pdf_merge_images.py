import os
import logging
import subprocess

import aiofiles
import natsort
from fastapi import APIRouter
from fastapi import (
	File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	cleanup_temp_dir, get_temp_pdf_path, validate_image_file_input,
)

logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_merge_images_router = APIRouter(
	tags=["PDF Merge API"],
	responses={404: {"description": "Not found"}},
)

GENERIC_FAIL_ERROR = "Error generating PDF from images"


@pdf_merge_images_router.post(
	urls.get("view_pdf_merge_images"),
	include_in_schema=True,
)
async def merge_images(
		background_tasks: BackgroundTasks,
		files: list[UploadFile] = File(...),
		use_upload_order: bool = Query(False),
		token_data: bool = Depends(verify_token),
) -> FileResponse:
	"""Merge images (ex: document scans) into a single PDF."""
	if len(files) > 30:
		raise HTTPException(
			status_code=400, detail="You can upload a maximum of 20 PDFs"
		)

	for file in files:
		validate_image_file_input(file)

	new_pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(new_pdf_path)

	try:
		img_files_paths = []
		for file in files:
			img_file_path = os.path.join(temp_dir, file.filename)

			async with aiofiles.open(img_file_path, "wb") as f:
				await f.write(await file.read())

			img_files_paths.append(img_file_path)

		if not use_upload_order:
			img_files_paths = natsort.natsorted(img_files_paths)

		command = ["img2pdf",]

		command.extend(img_files_paths)
		command.extend(["-o", new_pdf_path])

		result = subprocess.run(command, capture_output=True, text=True)

		if result.returncode != 0:
			raise HTTPException(
				status_code=500,
				detail=GENERIC_FAIL_ERROR
			)

		if not os.path.exists(new_pdf_path):
			raise HTTPException(
				status_code=500,
				detail=GENERIC_FAIL_ERROR
			)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
		return FileResponse(
			new_pdf_path, media_type='application/pdf',
			filename='output.pdf'
		)

	except (OSError, Exception, HTTPException) as e:
		logging.error(f"Error: {e}")
		if isinstance(e, HTTPException):
			raise HTTPException(
				status_code=e.status_code,
				detail=GENERIC_FAIL_ERROR
			)
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
