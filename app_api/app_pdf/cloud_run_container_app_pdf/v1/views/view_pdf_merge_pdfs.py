import io
import os
import logging

import natsort
from pypdf import PdfReader, PdfWriter
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	cleanup_temp_dir, validate_pdf_file_input, get_temp_pdf_path,
)

logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_merge_pdfs_router = APIRouter(
	tags=["PDF Merge API"],
	responses={404: {"description": "Not found"}},
)

MAX_PDF_FILES = 20


@pdf_merge_pdfs_router.post(
	urls.get("view_pdf_merge_pdfs"),
	include_in_schema=True,
)
async def merge_pdfs(
		background_tasks: BackgroundTasks,
		files: list[UploadFile] = File(...),
		use_upload_order: bool = Query(False),
		token_data: bool = Depends(verify_token),
) -> FileResponse:
	if len(files) > MAX_PDF_FILES:
		raise HTTPException(
			status_code=400,
			detail=f"You can upload a maximum of {MAX_PDF_FILES} PDFs."
		)

	for file in files:
		validate_pdf_file_input(file)

	if not use_upload_order:
		files = natsort.natsorted(files, key=lambda x: x.filename)

	new_pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(new_pdf_path)

	writer = PdfWriter()
	try:
		for file in files:
			# Read the file
			file_content = await file.read()
			# Load the PDF
			file_stream = io.BytesIO(file_content)
			pdf_doc = PdfReader(file_stream)
			# Append each page of the PDF to the merged PDF
			for page in pdf_doc.pages:
				writer.add_page(page)

		# Save the merged PDF
		with open(new_pdf_path, "wb") as f:
			writer.write(f)
		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
		return FileResponse(
			new_pdf_path, media_type='application/pdf',
			filename='output.pdf'
		)

	except OSError as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
