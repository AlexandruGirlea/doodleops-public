"""
We send the password using FieldForm, because we don't want the password in the
URL, because Swagger UI will not show the filed, but the OpenAPI Docs
will show the field.
"""
import os
import string
import logging
import itertools
from urllib.parse import unquote

from pypdf import PdfReader, PdfWriter
from fastapi import (
	File, UploadFile, HTTPException, BackgroundTasks, Depends, Form, APIRouter
)
from fastapi.responses import FileResponse, JSONResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	cleanup_temp_dir, get_random_file_name, validate_pdf_file_input,
	get_temp_pdf_path,
)

logger = logging.getLogger("APP_PDF_V1_"+__name__)

password_manager_router = APIRouter(
	tags=["PDF Password Management"],
	responses={404: {"description": "Not found"}},
)

NO_PASS_ERR_MSG = "PDF is not password protected."
PASS_PROTECTED_ERR_MSG = "PDF is password protected."
INCORRECT_PASS_ERR_MSG = "Incorrect password."


@password_manager_router.post(
	urls.get("view_pdf_password_management").get("add"),
	include_in_schema=True,
)
async def add_password(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(..., description="PDF file to upload"),
		password: str = Form(
			...,
			min_length=1,
			max_length=50,
			description="Password to be added to the PDF file",
		),
		token_data: bool = Depends(verify_token),
):
	if not password:
		raise HTTPException(status_code=400, detail="Password is required")
	password = unquote(password)
	validate_pdf_file_input(file)

	pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(pdf_path)

	try:
		with open(pdf_path, "wb") as f:
			f.write(await file.read())

		output_pdf_path = os.path.join(
			os.path.dirname(pdf_path), f"{get_random_file_name()}.pdf"
		)
		reader = PdfReader(pdf_path)
		if reader.is_encrypted:
			raise ValueError(PASS_PROTECTED_ERR_MSG)

		writer = PdfWriter()
		for page in range(len(reader.pages)):
			writer.add_page(reader.pages[page])

		writer.encrypt(user_password=password, owner_password=password)
		with open(output_pdf_path, "wb") as f:
			writer.write(f)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)

		return FileResponse(
			output_pdf_path, media_type='application/pdf',
			filename='output.pdf'
		)

	except ValueError as e:
		if str(e) == PASS_PROTECTED_ERR_MSG:
			raise HTTPException(status_code=400, detail=PASS_PROTECTED_ERR_MSG)
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=400, detail="Bad request")

	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=500, detail="Server error")


@password_manager_router.post(
	urls.get("view_pdf_password_management").get("remove"),
	include_in_schema=True,
)
async def remove_password(
		background_tasks: BackgroundTasks,
		password: str = Form(
			...,
			min_length=1,
			max_length=50,
			description="Password to be added to the PDF file",
		),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	if not password:
		raise HTTPException(status_code=400, detail="Password is required")
	password = unquote(password)
	validate_pdf_file_input(file)
	pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(pdf_path)

	try:
		with open(pdf_path, "wb") as f:
			f.write(await file.read())

		output_pdf_path = os.path.join(
			os.path.dirname(pdf_path), f"{get_random_file_name()}.pdf"
		)

		reader = PdfReader(pdf_path)

		if not reader.is_encrypted:
			raise ValueError(NO_PASS_ERR_MSG)

		if not reader.decrypt(password):
			raise ValueError(INCORRECT_PASS_ERR_MSG)

		writer = PdfWriter()
		# Add pages to the writer from the decrypted reader
		for page in reader.pages:
			writer.add_page(page)

		with open(output_pdf_path, "wb") as f:
			writer.write(f)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)

		return FileResponse(
			output_pdf_path, media_type='application/pdf',
			filename='output.pdf'
		)

	except ValueError as e:
		if str(e) in (NO_PASS_ERR_MSG, INCORRECT_PASS_ERR_MSG):
			raise HTTPException(status_code=400, detail=str(e))
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=400, detail="Bad request")

	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=500, detail="Server error")


@password_manager_router.post(
	urls.get("view_pdf_password_management").get("change"),
	include_in_schema=True,
)
async def change_password(
		background_tasks: BackgroundTasks,
		old_password: str = Form(
			...,
			min_length=1,
			max_length=50,
			description="Password to be added to the PDF file",
		),
		new_password: str = Form(
			...,
			min_length=1,
			max_length=50,
			description="Password to be added to the PDF file",
		),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	if not old_password or not new_password:
		raise HTTPException(
			status_code=400, detail="Both old and new passwords are required"
		)
	old_password = unquote(old_password)
	new_password = unquote(new_password)
	validate_pdf_file_input(file)

	pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(pdf_path)

	try:
		with open(pdf_path, "wb") as f:
			f.write(await file.read())

		output_pdf_path = os.path.join(
			os.path.dirname(pdf_path), f"{get_random_file_name()}.pdf"
		)

		reader = PdfReader(pdf_path)

		if not reader.is_encrypted:
			raise ValueError(NO_PASS_ERR_MSG)

		if not reader.decrypt(old_password):
			raise ValueError(INCORRECT_PASS_ERR_MSG)

		writer = PdfWriter()
		# Add pages to the writer from the decrypted reader
		for page in reader.pages:
			writer.add_page(page)

		writer.encrypt(user_password=new_password, owner_password=new_password)

		with open(output_pdf_path, "wb") as f:
			writer.write(f)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)

		return FileResponse(
			output_pdf_path, media_type='application/pdf',
			filename='output.pdf'
		)

	except ValueError as e:
		if str(e) in (NO_PASS_ERR_MSG, INCORRECT_PASS_ERR_MSG):
			raise HTTPException(status_code=400, detail=str(e))
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=400, detail="Bad request")

	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
