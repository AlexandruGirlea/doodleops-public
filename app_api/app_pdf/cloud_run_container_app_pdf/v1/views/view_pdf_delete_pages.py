import os
import logging

from pypdf import PdfReader, PdfWriter
from fastapi import APIRouter
from fastapi import (
	File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	get_temp_pdf_path, cleanup_temp_dir, validate_pdf_file_input,
	get_random_file_name
)

logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_delete_pages_router = APIRouter(
	tags=["PDF Delete Pages"],
	responses={404: {"description": "Not found"}},
)


INVALID_PAGE_NUMBER_ERROR = "Invalid page numbers provided"


@pdf_delete_pages_router.post(
	urls.get("view_pdf_delete_pages"),
	include_in_schema=True,
)
async def pdf_delete_pages(
		background_tasks: BackgroundTasks,
		pages_to_remove: str = Query(
			...,
			max_length=200,
			description="Comma separated page numbers to remove from the PDF file"
		),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	if not pages_to_remove.replace(',', '').isdigit():
		raise HTTPException(status_code=400, detail=INVALID_PAGE_NUMBER_ERROR)

	validate_pdf_file_input(file)

	pages_to_remove = [int(page)-1 for page in pages_to_remove.split(',')]

	pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(pdf_path)
	random_name = get_random_file_name()
	try:
		with open(pdf_path, "wb") as f:
			f.write(await file.read())

		reader = PdfReader(pdf_path)
		number_of_pages = len(reader.pages)

		# check if the page numbers are valid
		if ( number_of_pages <= 1 or
			not all(-1 < n <= number_of_pages for n in pages_to_remove)
			):
			raise HTTPException(status_code=400, detail=INVALID_PAGE_NUMBER_ERROR)
		writer = PdfWriter()

		for page_number in range(number_of_pages):
			if page_number not in pages_to_remove:
				# If the page is not in the list of pages to remove, add it to the new PDF
				writer.add_page(reader.pages[page_number])

		new_pdf_path = os.path.join(temp_dir, f'{random_name}.pdf')
		# Save the new PDF to the desired path
		with open(new_pdf_path, "wb") as f:
			writer.write(f)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)

		return FileResponse(
			new_pdf_path, media_type='application/pdf', filename='output.pdf'
		)
	except ValueError as e:
		if str(e) == INVALID_PAGE_NUMBER_ERROR:
			raise HTTPException(status_code=400, detail=INVALID_PAGE_NUMBER_ERROR)
		logging.error(f"Error: {e}")
		cleanup_temp_dir(temp_dir=temp_dir)
		raise HTTPException(status_code=400, detail=INVALID_PAGE_NUMBER_ERROR)
	except OSError as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(temp_dir=temp_dir)
		raise HTTPException(status_code=500, detail="Server error")
	except HTTPException as e:
		cleanup_temp_dir(temp_dir=temp_dir)
		raise e
	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(temp_dir=temp_dir)
		raise HTTPException(status_code=500, detail="Server error")
