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
from schemas.view_pdf_page_order import MAX_CHAR_REGEX

logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_page_order_router = APIRouter(
	tags=["PDF Page Order"],
	responses={404: {"description": "Not found"}},
)

INVALID_PAGE_ORDER_ERROR = "Invalid page order"
GENERIC_ERROR_MSG = "Failed to create new PDF."


@pdf_page_order_router.post(
	urls.get("view_pdf_page_order"),
	include_in_schema=True,
)
async def pdf_order(
		background_tasks: BackgroundTasks,
		page_order: str = Query(
			..., description="ex: `2,1,3,4`", regex=MAX_CHAR_REGEX
		),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
) -> FileResponse:

	validate_pdf_file_input(file)

	page_order = page_order.replace(" ", "")

	if not page_order or not page_order.replace(",", "").isdigit():
		raise HTTPException(status_code=400, detail=INVALID_PAGE_ORDER_ERROR)

	page_order = [int(i) - 1 for i in page_order.split(",")]
	clean_order = []

	# remove duplicates
	for i in page_order:
		if i not in clean_order:
			clean_order.append(i)


	if any(i < 0 for i in clean_order):
		raise HTTPException(status_code=400, detail=INVALID_PAGE_ORDER_ERROR)

	new_pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(new_pdf_path)

	try:
		with io.BytesIO(await file.read()) as file_stream:
			pdf_reader = PdfReader(file_stream)
			total_pages = len(pdf_reader.pages)

			# Create the list of remaining pages
			all_page_indices = list(range(total_pages))
			remaining_pages = [
				i for i in all_page_indices if i not in clean_order
			]

			# Total order of pages
			total_order = clean_order + remaining_pages

			with PdfWriter() as pdf_writer:
				# Reorder pages according to total_order
				for page_num in total_order:
					pdf_writer.add_page(pdf_reader.pages[page_num])

				with open(new_pdf_path, "wb") as output_pdf:
					pdf_writer.write(output_pdf)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
		return FileResponse(
			new_pdf_path, media_type='application/pdf',
			filename='output.pdf'
		)

	except ValueError as e:
		if str(e) == INVALID_PAGE_ORDER_ERROR:
			cleanup_temp_dir(file_path=new_pdf_path)
			raise HTTPException(status_code=400, detail=str(e))
		else:
			logging.error(f"Error: {e}")
			cleanup_temp_dir(file_path=new_pdf_path)
			raise HTTPException(status_code=500, detail=GENERIC_ERROR_MSG)
	except OSError as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail=GENERIC_ERROR_MSG)
	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail=GENERIC_ERROR_MSG)
