import logging

from pydantic import BaseModel, validator
import barcode
from barcode.errors import (
	BarcodeNotFoundError, BarcodeError, IllegalCharacterError,
	NumberOfDigitsError, WrongCountryCodeError
)
from barcode.writer import ImageWriter
from fastapi import APIRouter
from fastapi import HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import get_temp_file_path, cleanup_temp_dir

logger = logging.getLogger(__name__)

image_create_barcode_router = APIRouter(
	tags=["QR & Bar Codes"],
	responses={404: {"description": "Not found"}},
)


class CreateBarcode(BaseModel):
	text: str
	code_type: str = f"Ex: {','.join(barcode.PROVIDED_BARCODES)}"

	@validator("code_type")
	def validate_type(cls, v):
		if v.lower() not in barcode.PROVIDED_BARCODES:
			raise ValueError("Invalid barcode type")
		return v.lower()


@image_create_barcode_router.post(
	urls.get("read_codes").get("create_barcode"),
	include_in_schema=True,
)
async def create_barcode(
		background_tasks: BackgroundTasks,
		barcode_data: CreateBarcode,
		token_data: bool = Depends(verify_token),
):

	output_file_path = get_temp_file_path(extension="png")

	try:

		code = barcode.get(
			name=barcode_data.code_type,
			code=barcode_data.text,
			writer=ImageWriter()
		)

		code.save(output_file_path.split(".png")[0])

		background_tasks.add_task(cleanup_temp_dir, file_path=output_file_path)

		return FileResponse(
			output_file_path,
			media_type="image/png",
			filename=f"{barcode_data.text}.png",
		)
	except (
			BarcodeNotFoundError, BarcodeError, IllegalCharacterError,
			NumberOfDigitsError, WrongCountryCodeError
	) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=400, detail="Invalid barcode data")

	except (Exception, OSError) as e:
		cleanup_temp_dir(file_path=output_file_path)
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
