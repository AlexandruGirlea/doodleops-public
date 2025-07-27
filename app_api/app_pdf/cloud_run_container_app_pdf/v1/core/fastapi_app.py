import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from views.view_pdf_convert_to_image import pdf_convert_format_to_image_router
from views.view_pdf_delete_pages import pdf_delete_pages_router
from views.view_pdf_password_management import password_manager_router
from views.view_pdf_rotate import pdf_rotate_pages_router
from views.view_pdf_watermark import pdf_watermark_router
from views.view_pdf_split import pdf_split_router
from views.view_pdf_merge_pdfs import pdf_merge_pdfs_router
from views.view_pdf_merge_images import pdf_merge_images_router
from views.view_pdf_page_order import pdf_page_order_router
from views.view_pdf_insert_pdf import pdf_insert_pdf_router
from views.view_pdf_extract_images import pdf_extract_images_router
from views.view_pdf_extract_tables import pdf_extract_tables_from_text_pdf_router
from core.tracing import setup_fastapi_tracing
from uvicorn_config import log_config_gcp


if os.getenv("ENV_MODE") == "local":
    app = FastAPI(docs_url="/swagger", redoc_url="/doc")
else:
    app = FastAPI(docs_url=None, redoc_url=None)
    logging.config.dictConfig(log_config_gcp)
    setup_fastapi_tracing(app)

app.include_router(pdf_convert_format_to_image_router)
app.include_router(pdf_delete_pages_router)
app.include_router(password_manager_router)
app.include_router(pdf_rotate_pages_router)
app.include_router(pdf_watermark_router)
app.include_router(pdf_split_router)
app.include_router(pdf_merge_pdfs_router)
app.include_router(pdf_merge_images_router)
app.include_router(pdf_page_order_router)
app.include_router(pdf_insert_pdf_router)
app.include_router(pdf_extract_images_router)
app.include_router(pdf_extract_tables_from_text_pdf_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=[os.getenv("ALLOWED_METHODS", "*")],
    allow_headers=[os.getenv("ALLOWED_HEADERS", "*")],
)
