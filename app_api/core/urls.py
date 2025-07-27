"""
Structure of the urls for the API.
Use `is_active` to enable or disable the APIs.
"""
from schemas.urls import ExternalAPIEndpoint
from app_docs.views.v1.urls import app_docs_v1_urls
from app_epub.views.v1.urls import app_epub_v1_urls
from app_images.views.v1.urls import app_images_v1_urls
from app_pdf.views.v1.urls import app_pdf_v1_urls
from app_ai.views.v1.urls import app_ai_v1_urls
from views.urls import default_urls

cloud_run_app_urls = {
	"app_docs": {
		"v1": {**app_docs_v1_urls}
	},
	"app_epub": {
		"v1": {**app_epub_v1_urls}
	},
	"app_images": {
		"v1": {**app_images_v1_urls}
	},
	"app_pdf": {
		"v1": {**app_pdf_v1_urls}
	},
	"app_ai": {
		"v1": {**app_ai_v1_urls}
	},
}

default_api_urls = {
	"default":
		{
			"v1": {**default_urls}
		}
}

urls = {
	**cloud_run_app_urls,
	**default_api_urls
}
