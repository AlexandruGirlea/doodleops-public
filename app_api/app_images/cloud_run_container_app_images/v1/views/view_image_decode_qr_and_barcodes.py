import logging

import cv2
import numpy as np
from pyzbar.pyzbar import decode
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import read_image_from_file_upload

logger = logging.getLogger(__name__)

image_decode_qr_and_barcodes_router = APIRouter(
	tags=["QR & Bar Codes"],
	responses={404: {"description": "Not found"}},
)


@image_decode_qr_and_barcodes_router.post(
	urls.get("read_codes").get("decode_qr_and_barcodes"),
	include_in_schema=True,
)
async def decode_qr_and_barcodes(
		file: UploadFile = File(...),
		token_data: bool = Depends(verify_token),
):
	image = await read_image_from_file_upload(file)

	try:

		decoded_objects = decode(image)

		if not decoded_objects:
			# Check for QR code in the image with OpenCV
			img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
			detector = cv2.QRCodeDetector()
			data, vertices_array, _ = detector.detectAndDecode(img_cv)

			if data:
				return JSONResponse(
					status_code=200,
					content={"codes": [{"type": "QR", "data": data}]}
				)

			return HTTPException(
				status_code=400, detail="No QR or barcode found in the image."
			)

		list_of_qr_codes = []
		for obj in decoded_objects:
			list_of_qr_codes.append(obj.data.decode("utf-8"))

		return JSONResponse(
			status_code=200,
			content={
				"codes":
					[
						{"type": obj.type, "data": obj.data.decode("utf-8")}
						for obj in decoded_objects
					]
				},
		)

	except OSError as e:
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
	except Exception as e:
		logging.error(f"Error: {e}")
		raise HTTPException(status_code=500, detail="Server error")
