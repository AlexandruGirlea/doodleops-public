import os
import logging

import cv2
import pytesseract
from PIL import Image
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
    cleanup_temp_dir, read_image_from_file_upload, get_temp_file_path,
    get_iso_639_2_languages,
)


logger = logging.getLogger(__name__)

image_ocr_router = APIRouter(
    tags=["General"],
    responses={404: {"description": "Not found"}},
)


ALLOWED_EXTENSIONS = {
    'jpeg': 'JPEG',
    'jpg': 'JPEG',
    'jpe': 'JPEG',
    'png': 'PNG',
    'bmp': 'BMP',
    'dib': 'BMP',
    'tiff': 'TIFF',
    'tif': 'TIFF',
}


@image_ocr_router.post(
    urls.get("general").get("ocr"),
    include_in_schema=True,
)
async def ocr_image(
        background_tasks: BackgroundTasks,
        language: str = Query("eng", description="Language code for OCR"),
        file: UploadFile = File(...),
        token_data: bool = Depends(verify_token),
):
    image = await read_image_from_file_upload(file)
    extension = file.filename.split('.')[-1]

    if not extension.lower() in ALLOWED_EXTENSIONS.keys():
        raise HTTPException(status_code=400, detail="Invalid file format")

    iso_639_2_languages = get_iso_639_2_languages()
    if language not in iso_639_2_languages.keys():
        raise HTTPException(status_code=400, detail="Invalid language code")

    image_path = get_temp_file_path(extension)
    temp_dir = os.path.dirname(image_path)

    image.save(image_path)
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        resized = cv2.resize(thresh, None, fx=2, fy=2,
                             interpolation=cv2.INTER_LINEAR)
        preprocessed_image_path = os.path.join(
            temp_dir, f"preprocessed_{file.filename}"
        )
        cv2.imwrite(preprocessed_image_path, resized)

        with Image.open(preprocessed_image_path) as img:
            text = pytesseract.image_to_string(img, lang=language)

        background_tasks.add_task(cleanup_temp_dir, file_path=image_path)
        if text and text.endswith("\x0c"):
            text = text[:-1]
        return JSONResponse(content={"text": text})

    except OSError as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=image_path)
        raise HTTPException(status_code=500, detail="Server error")
    except Exception as e:
        logging.error(f"Error: {e}")
        cleanup_temp_dir(file_path=image_path)
        raise HTTPException(status_code=500, detail="Server error")
