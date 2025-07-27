import io
import os
import zipfile
import logging

from pypdf import PdfReader
from PIL import Image
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	cleanup_temp_dir, validate_pdf_file_input, get_temp_pdf_path,
)

logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_extract_images_router = APIRouter(
	tags=["PDF Extract Images"],
	responses={404: {"description": "Not found"}},
)


@pdf_extract_images_router.post(
	urls.get("view_pdf_extract_images"),
	include_in_schema=True,
)
async def extract_images_from_pdf(
		background_tasks: BackgroundTasks,
		pages: str = Query(
			None,
			description="Comma separated page numbers to extract images from"
		),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
) -> FileResponse:
	validate_pdf_file_input(file)

	if pages and not pages.replace(",", "").isdigit():
		raise HTTPException(status_code=400, detail="Invalid page numbers")

	pages = [int(page) - 1 for page in pages.split(",")] if pages else None

	if pages and any(page < 0 for page in pages):
		raise HTTPException(status_code=400, detail="Invalid page numbers")

	new_pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(new_pdf_path)

	try:
		file_stream = io.BytesIO(await file.read())
		pdf_doc = PdfReader(file_stream)

		pages_to_process = range(len(pdf_doc.pages)) if pages is None else pages

		image_counter = 1
		for page_number in pages_to_process:
			page = pdf_doc.pages[page_number]
			for img_name, image in page.images.items():
				image_obj = Image.open(io.BytesIO(image.data))
				if image_obj.mode == 'RGBA':
					image_obj = image_obj.convert('RGB')
				img_path = os.path.join(
					temp_dir, f"image_{image_counter}.jpeg"
				)
				image_obj.save(img_path, "JPEG")
				image_counter += 1

		zip_filename = "extracted_images.zip"
		zip_file_path = os.path.join(temp_dir, zip_filename)
		with zipfile.ZipFile(zip_file_path, 'w') as zipf:
			for root, dirs, files in os.walk(temp_dir):
				for file in files:
					if file.endswith(".jpeg"):
						zipf.write(os.path.join(root, file), file)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
		return FileResponse(
			path=zip_file_path,
			filename=zip_filename,
			media_type="application/zip"
		)

	except OSError as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=new_pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
