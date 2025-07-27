import os
import logging
from enum import Enum

import camelot
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	cleanup_temp_dir, validate_pdf_file_input, get_temp_pdf_path,
	convert_pandas_to_excel, archive_to_zip
)
from schemas.view_pdf_extract_tables import (
	Payload, FlavorEnum, OutputOptions, OutputFormat
)

logger = logging.getLogger("APP_PDF_V1_"+__name__)

pdf_extract_tables_from_text_pdf_router = APIRouter(
	tags=["PDF Extract Tables from Text PDF"],
	responses={404: {"description": "Not found"}},
)

EXCEL_MEDIA_TYPE = (
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
NO_TABLES_FOUND = "No tables found"



@pdf_extract_tables_from_text_pdf_router.post(
	urls.get("view_pdf_extract_tables"),
	include_in_schema=True,
)
async def extract_tables_from_text_pdf(
		background_tasks: BackgroundTasks,
		payload: Payload = Depends(),
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
) -> FileResponse:
	validate_pdf_file_input(file)

	pdf_path = get_temp_pdf_path()
	temp_dir = os.path.dirname(pdf_path)
	zip_filename = "extracted_tables.zip"
	zip_file_path = os.path.join(temp_dir, zip_filename)
	excel_name = "extracted_tables.xlsx"
	excel_path = os.path.join(temp_dir, excel_name)


	try:
		with open(pdf_path, "wb") as pdf_file:
			pdf_file.write(await file.read())

		clean_payload = {}
		for k, v in payload.dict().items():
			if not v:
				continue
			elif v is not None:
				clean_payload[k] = v if not isinstance(v, Enum) else v.value

		output_format = clean_payload.pop("output_format")
		output_options = clean_payload.pop("output_options")

		if (
				clean_payload.get("flavor") == FlavorEnum.stream.value and
				clean_payload.get("table_areas")
		):
			clean_payload.pop("process_background")
		tables = camelot.read_pdf(pdf_path, **clean_payload)

		if not tables:
			raise HTTPException(status_code=200, detail=NO_TABLES_FOUND)

		if (
				output_format == OutputFormat.excel.value and
				output_options == OutputOptions.one_excel.value  # multiple sheets
		) or (
				output_format == OutputFormat.excel.value and
				len(tables) == 1  # does not matter, can't create multiple excels
		):

			convert_pandas_to_excel(
				df_tables=[t.df for t in tables],
				excel_path=excel_path
			)

			background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
			return FileResponse(
				path=excel_path,
				filename=excel_name,
				media_type=EXCEL_MEDIA_TYPE
			)
		elif (
				output_format == OutputFormat.excel.value and
				output_options == OutputOptions.multiple_excels.value
		):
			convert_pandas_to_excel(
				df_tables=[t.df for t in tables],
				excel_path=excel_path,
				multiple_files=True
			)

			archive_to_zip(
				zip_file_path=zip_file_path,
				file_extension=".xlsx"
			)

			background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
			return FileResponse(
				path=zip_file_path,
				filename=zip_filename,
				media_type="application/zip"
			)
		elif output_format == OutputFormat.csv:
			if len(tables) == 1:
				tables[0].to_csv(
					os.path.join(temp_dir, "table.csv"),
					index=False
				)
				return FileResponse(
					path=os.path.join(temp_dir, "table.csv"),
					filename="table.csv",
					media_type="text/csv"
				)

			for table_number, table in enumerate(tables):
				table.to_csv(
					os.path.join(temp_dir, f"table_{table_number}.csv"),
					index=False
				)

			archive_to_zip(
				zip_file_path=zip_file_path,
				file_extension=".csv"
			)

			background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
			return FileResponse(
				path=zip_file_path,
				filename=zip_filename,
				media_type="application/zip"
			)
		else:
			cleanup_temp_dir(file_path=pdf_path)
			raise HTTPException(status_code=400, detail="Invalid output options")

	except OSError as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
	except Exception as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=pdf_path)
		raise HTTPException(status_code=500, detail="Server error")
