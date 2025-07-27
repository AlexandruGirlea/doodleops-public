"""Insert PDF into PDF after page number."""

import io
import os
import logging

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

pdf_insert_pdf_router = APIRouter(
	tags=["PDF Insert API"],
	responses={404: {"description": "Not found"}},
)

PAGE_NUMBER_OUT_OF_RANGE = "Page number out of range"


@pdf_insert_pdf_router.post(
	urls.get("view_pdf_insert_pdf"),
	include_in_schema=True,
)
async def insert_pdf(
		background_tasks: BackgroundTasks,
		after_page_number: int = Query(
			None, description="Page number after which to insert the PDF"
		),
		base_file: UploadFile = File(...),
		insert_file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
) -> FileResponse:
	validate_pdf_file_input(base_file)
	validate_pdf_file_input(insert_file)

	new_pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(new_pdf_path)

	writer = PdfWriter()
	try:
		base_file_stream = io.BytesIO(await base_file.read())
		base_pdf_doc = PdfReader(base_file_stream)

		insert_file_stream = io.BytesIO(await insert_file.read())
		insert_pdf_doc = PdfReader(insert_file_stream)

		if after_page_number is not None and after_page_number < 0:
			raise ValueError(PAGE_NUMBER_OUT_OF_RANGE)

		for i, page in enumerate(base_pdf_doc.pages):
			if i == after_page_number:
				for insert_page in insert_pdf_doc.pages:
					writer.add_page(insert_page)
			writer.add_page(page)

		# if not after_page_number add after base file
		if (
				after_page_number is None or
				after_page_number >= len(base_pdf_doc.pages)
		):
			for insert_page in insert_pdf_doc.pages:
				writer.add_page(insert_page)

		with open(new_pdf_path, "wb") as f:
			writer.write(f)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
		return FileResponse(
			new_pdf_path, media_type='application/pdf',
			filename="new_merged.pdf"
		)

	except ValueError as e:
		if str(e) == PAGE_NUMBER_OUT_OF_RANGE:
			raise HTTPException(status_code=400, detail=PAGE_NUMBER_OUT_OF_RANGE)
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
	except OSError as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
