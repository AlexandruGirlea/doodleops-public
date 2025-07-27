import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.tracing import setup_fastapi_tracing
from views.view_epub_convert import file_convert_router

if os.getenv("ENV_MODE") == "local":
    app = FastAPI(docs_url="/swagger", redoc_url="/doc")
else:
    app = FastAPI(docs_url=None, redoc_url=None)

setup_fastapi_tracing(app)
app.include_router(file_convert_router)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=[os.getenv("ALLOWED_METHODS", "*")],
    allow_headers=[os.getenv("ALLOWED_HEADERS", "*")],
)
