from fastapi import Request
from fastapi.responses import JSONResponse

from core.urls import urls
from schemas.urls import CloudRunAPIEndpoint
from app_pdf.views.v1.openai_views.route import v1_view_pdf_router_openai

APP_NAME, VERSION, API = "app_pdf", "v1", "view_pdf_openai_well_known_manifest"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]


@v1_view_pdf_router_openai.get(URL_DATA.api_url, include_in_schema=True)
async def view_well_known_manifest_pdf(request: Request):
	data = {
		"schema_version": "v1",
		"name_for_human": "Doodle PDF Utilities",
		"name_for_model": "doodleops_pdf_utils",
		"description_for_human": (
			"DoodleOps is a powerful PDF manipulation service that allows you to "
			"transform your PDF documents in a variety of ways. With DoodleOps, "
			"you can easily convert PDFs to images or Word documents, remove or "
			"reorder pages, merge multiple PDFs or images into a single PDF, "
			"extract images and tables, insert one PDF into another, and split "
			"large PDFs into smaller ones. You can also manage PDF passwords "
			"(add, change, or remove) and apply image or text watermarks. "
			"Whether you need to convert, edit, protect, or enhance your PDFs, "
			"DoodleOps simplifies your workflow."
		),
		"description_for_model": (
			"DoodleOps provides endpoints for comprehensive PDF manipulation. "
			"The API supports PDF-to-image and PDF-to-Word conversions, page "
			"removal, reordering, and insertion operations, as well as merging "
			"images or PDFs and splitting large files. Additional features "
			"include extracting images or tables from PDFs, "
			"adding/changing/removing passwords for security, "
			"rotating pages, and applying watermarks (either images or text). "
			"Use the endpoints to automate PDF editing tasks, integrate PDF "
			"transformations into workflows, and reliably produce the desired "
			"output format and configuration."
		),
		"auth": {
			"type": "oauth",
			"authorization_url": "https://doodleops.com/o/authorize",
			"token_url": "https://doodleops.com/o/token",
			"scopes": ["read", "write"],
			"authorization_type": "bearer"
		},
		"api": {
			"type": "openapi",
			"url": "https://api.doodleops.com/pdf/v1/openapi.json",
			"is_user_authenticated": True
		},
		"logo_url": "https://static.doodleops.com/logo.png",
		"contact_email": "support@doodleops.com",
		"legal_info_url": "https://doodleops.com/privacy/"
	}
	return JSONResponse(content=data, status_code=200)
