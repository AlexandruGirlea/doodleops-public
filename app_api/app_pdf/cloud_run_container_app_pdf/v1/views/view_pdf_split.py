import os
import logging
import zipfile

from pypdf import PdfReader, PdfWriter
from fastapi import (
	File, UploadFile, HTTPException, BackgroundTasks, Depends, Query, APIRouter
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	cleanup_temp_dir, validate_pdf_file_input, get_temp_pdf_path,
	get_random_file_name
)

logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_split_router = APIRouter(
	tags=["PDF Split API"],
	responses={404: {"description": "Not found"}},
)

EMPTY_PDF_ERROR = "The PDF file is empty"
SINGLE_PAGE_PDF_ERROR = "The PDF file has only one page"
MAX_NUM_PAGES = 200
MAX_NUM_PAGES_ERROR = f"PDF file has more than {MAX_NUM_PAGES} pages."



@pdf_split_router.post(
	urls.get("view_pdf_split"),
	include_in_schema=True,
)
async def pdf_split(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	validate_pdf_file_input(file)
	pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(pdf_path)
	random_name = get_random_file_name()
	try:
		with open(pdf_path, "wb") as f:
			f.write(await file.read())

		list_of_pdfs = []

		with open(pdf_path, "rb") as pdf_file:
			pdf_document = PdfReader(pdf_file)
			num_pages = len(pdf_document.pages)

			if num_pages > MAX_NUM_PAGES:
				raise ValueError(MAX_NUM_PAGES_ERROR)

			if num_pages == 0:
				raise ValueError(EMPTY_PDF_ERROR)
			elif num_pages == 1:
				raise ValueError(SINGLE_PAGE_PDF_ERROR)

			for page_num in range(num_pages):
				writer = PdfWriter()
				# Create a new PDF for the single page
				writer.add_page(pdf_document.pages[page_num])

				# Define the output path
				output_pdf_path = os.path.join(
					temp_dir, f"output-{page_num + 1}.pdf")
				list_of_pdfs.append(output_pdf_path)

				with open(output_pdf_path, "wb") as output_pdf_file:
					writer.write(output_pdf_file)

		zip_path = os.path.join(temp_dir, f'{random_name}.zip')
		with zipfile.ZipFile(zip_path, 'w') as zipf:
			for i in list_of_pdfs:
				zipf.write(i)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
		return FileResponse(
			zip_path, media_type='application/zip',
			filename='output.zip'
		)

	except ValueError as e:
		if str(e) in (
				EMPTY_PDF_ERROR, SINGLE_PAGE_PDF_ERROR, MAX_NUM_PAGES_ERROR
		):
			cleanup_temp_dir(temp_dir=temp_dir)
			raise HTTPException(status_code=400, detail=str(e))
		else:
			logging.error(f"Error: {e}")
			cleanup_temp_dir(temp_dir=temp_dir)
			raise HTTPException(status_code=500, detail="Server error")

	except OSError as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(temp_dir=temp_dir)
		raise HTTPException(status_code=500, detail="Server error")
	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(temp_dir=temp_dir)
		raise HTTPException(status_code=500, detail="Server error")
