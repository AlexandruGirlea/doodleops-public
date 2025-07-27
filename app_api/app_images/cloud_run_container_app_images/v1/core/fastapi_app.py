import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from views.view_image_rotate import image_rotate_router
from views.view_image_create_gif import image_create_gif_router
from views.view_image_gif_extract_frames import image_gif_extract_frames_router
from views.view_image_crop import image_crop_router
from views.view_image_ocr import image_ocr_router
from views.view_image_create_qr_code import image_create_qr_code_router
from views.view_image_compare_images import image_compare_images_router
from views.view_image_decode_qr_and_barcodes import (
    image_decode_qr_and_barcodes_router
)
from views.view_image_create_barcode import image_create_barcode_router
from views.view_image_cartoonify import image_cartoonify_router
from views.view_image_remove_background import image_remove_background_router
from views.view_image_downsize import image_downsize_router
from views.view_image_convert_format import image_convert_format_router
from views.view_image_convert_dicom_to_jpg import image_convert_dicom_to_jpg_router
from views.view_image_convert_to_b_w import image_convert_to_b_w_router
from views.view_image_convert_to_gray import image_convert_to_gray_router
from views.view_image_create_thumbnail import image_create_thumbnail_router
from views.view_image_create_ico import image_create_ico_router
from views.view_image_watermark_image import image_add_watermark_image_router
from views.view_image_watermark_text import image_add_watermark_text_router
from core.tracing import setup_fastapi_tracing


if os.getenv("ENV_MODE") == "local":
    app = FastAPI(docs_url="/swagger", redoc_url="/doc")
else:
    app = FastAPI(docs_url=None, redoc_url=None)

setup_fastapi_tracing(app)

app.include_router(image_rotate_router)
app.include_router(image_create_gif_router)
app.include_router(image_gif_extract_frames_router)
app.include_router(image_crop_router)
app.include_router(image_ocr_router)
app.include_router(image_create_qr_code_router)
app.include_router(image_decode_qr_and_barcodes_router)
app.include_router(image_compare_images_router)
app.include_router(image_create_barcode_router)
app.include_router(image_cartoonify_router)
app.include_router(image_remove_background_router)
app.include_router(image_downsize_router)
app.include_router(image_convert_format_router)
app.include_router(image_convert_dicom_to_jpg_router)
app.include_router(image_convert_to_b_w_router)
app.include_router(image_convert_to_gray_router)
app.include_router(image_create_thumbnail_router)
app.include_router(image_create_ico_router)
app.include_router(image_add_watermark_image_router)
app.include_router(image_add_watermark_text_router)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=[os.getenv("ALLOWED_METHODS", "*")],
    allow_headers=[os.getenv("ALLOWED_HEADERS", "*")],
)
