import logging

from fastapi import Request
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.routes import *
from uvicorn_config import log_config_gcp
from core.main import app
from core import settings
from core.urls import urls
from core.tracing import setup_fastapi_tracing
from common.other import clean_openapi_schemas


if settings.ENV_MODE != "local":
    logging.config.dictConfig(log_config_gcp)
    setup_fastapi_tracing(app)

logger = logging.getLogger("APP_API")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    with open("VERSION") as f:
        version = f.read().strip()

    openapi_schema = get_openapi(
        title="DoodleOps API",
        version=version,
        summary="These are the API endpoints for DoodleOps",
        description="Please go to <a "
        "href='https://doodleops.com'>DoodleOps.com</a> for more "
        "information.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://static.doodleops.com/logo.png",
        "altText": "DoodleOps Logo",
    }

    return openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOW_METHODS,
    allow_headers=settings.ALLOW_HEADERS,
    # this is needed because Content-Disposition header contains the filename
    expose_headers=["Content-Disposition"],
)

# Default Routes
app.include_router(v1_default_view_router)

# App Docs Routers
app.include_router(v1_view_docs_router)

# App Epub Routers
app.include_router(v1_view_epub_router)

# App Images Routers
app.include_router(v1_view_images_router)

# App PDF Routers
app.include_router(v1_view_pdf_router)
app.include_router(v1_view_pdf_router_openai)

# App AI Routers
app.include_router(v1_view_ai_router)


@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(
            content=open("templates/404.html").read(), status_code=404
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )


@app.middleware("http")
async def check_api_toggle(request: Request, call_next):
    """
    This middleware checks if the endpoint is allowed to be called.
    It's used to toggle the API on and off.
    """
    relative_path = request.url.path.replace(settings.FASTAPI_BASE_URL, "")

    allowed_endpoints = {
        data.api_url
        for app_name, app_versions in urls.items()
        for app_version, app_endpoints in app_versions.items()
        for app_endpoint, data in app_endpoints.items()
        if data.is_active
    } | {
        "/",
        "/doc",
        "/openapi.json",
        "/favicon.ico",
        "9e68c24da9f5fd56991c.worker.js.map",
    }

    if settings.ENV_MODE == "prod" and relative_path not in allowed_endpoints:
        logger.warning(f"Endpoint {relative_path} is not allowed")
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    response = await call_next(request)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(*args):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request"},
    )


# create openapi.json view
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint(request: Request):
    openapi_schema = request.app.openapi()
    filtered_paths = {}
    for route_path, path_item in openapi_schema["paths"].items():
        if (
                not route_path.endswith(settings.ENDS_WITH_OPENAI) and
                route_path not in settings.HIDE_PRIVATE_API_PATHS
        ):
            filtered_paths[route_path] = path_item

    openapi_schema["paths"] = filtered_paths

    pruned_schemas = clean_openapi_schemas(
        openapi_schema=openapi_schema,
        filtered_paths=filtered_paths,
    )

    openapi_schema["components"]["schemas"] = pruned_schemas

    return JSONResponse(content=openapi_schema)


@app.get("/doc", include_in_schema=False)
def custom_redoc_ui():
    return HTMLResponse(
        content=settings.RE_DOC_HTML, status_code=200
    )


@app.get("/swagger", include_in_schema=False)
def custom_swagger_ui():
    if settings.ENV_MODE != "local":
        return HTMLResponse(
            content=open("templates/404.html").read(), status_code=404
        )

    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="My Custom Swagger UI",
    )
