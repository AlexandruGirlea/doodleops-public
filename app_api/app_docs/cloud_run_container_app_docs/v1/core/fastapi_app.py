import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from views.view_docs_excel_split import docs_excel_split_router
from views.view_docs_excel_merge import docs_excel_merge_router
from views.view_docs_excel_remove_rows_based_on_condition import (
    docs_excel_remove_rows_based_on_condition_router,
)
from views.view_docs_excel_extract_each_sheet_to_new_excels import (
    docs_excel_extract_each_sheet_to_new_excels_router,
)
from views.view_excel_find_and_replace import docs_find_and_replace_router
from views.view_docs_excel_remove_empty_rows import (
    docs_excel_remove_empty_rows_router,
)
from core.tracing import setup_fastapi_tracing

logger = logging.getLogger(__name__)


if os.getenv("ENV_MODE") == "local":
    app = FastAPI(docs_url="/swagger", redoc_url="/doc")
else:
    app = FastAPI(docs_url=None, redoc_url=None)

setup_fastapi_tracing(app)

app.include_router(docs_excel_split_router)
app.include_router(docs_excel_merge_router)
app.include_router(docs_excel_remove_empty_rows_router)
app.include_router(docs_excel_remove_rows_based_on_condition_router)
app.include_router(docs_excel_extract_each_sheet_to_new_excels_router)
app.include_router(docs_find_and_replace_router)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=[os.getenv("ALLOWED_METHODS", "*")],
    allow_headers=[os.getenv("ALLOWED_HEADERS", "*")],
)
