import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.settings import ENV_MODE
from core.tracing import setup_fastapi_tracing
from views.view_ai_twilio import ai_twilio_router
from uvicorn_config import log_config_gcp


if ENV_MODE == "local":
    app = FastAPI(docs_url="/swagger", redoc_url="/doc")
else:
    app = FastAPI(docs_url=None, redoc_url=None)
    logging.config.dictConfig(log_config_gcp)
    setup_fastapi_tracing(app)

app.include_router(ai_twilio_router)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=[os.getenv("ALLOWED_METHODS", "*")],
    allow_headers=[os.getenv("ALLOWED_HEADERS", "*")],
)
