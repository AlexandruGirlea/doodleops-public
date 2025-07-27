import copy
from os.path import join
from urllib.parse import urljoin

from core.settings import CLOUD_RUN_APPs
from schemas.urls import CloudRunAPIEndpoint, ExternalAPIEndpoint
from app_pdf.cloud_run_container_app_pdf.v1.views.urls import (
	urls as v1_urls_pdfs
)

app_pdf_v1_urls = {
	"view_pdf_convert_to_image": CloudRunAPIEndpoint(
		api_url=join(
			"/pdf/v1", v1_urls_pdfs["view_pdf_convert_to_image"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
				v1_urls_pdfs["view_pdf_convert_to_image"]
			)
		),
		is_active=True,
		other={
			"media_type": ["application/pdf"],
			"file_size_mb": 20,
		},
	),
	"view_pdf_convert_to_word_pro": ExternalAPIEndpoint(
				api_url="/pdf/v1/convert-to-word-pro",
				is_active=True,
				other={
					"media_type": ["application/pdf"],
					"file_size_mb": 20,
				},
			),

	"view_pdf_delete_pages": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1", v1_urls_pdfs["view_pdf_delete_pages"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_delete_pages"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_extract_images": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1", v1_urls_pdfs["view_pdf_extract_images"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_extract_images"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_extract_tables": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1",
				v1_urls_pdfs["view_pdf_extract_tables"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_extract_tables"]
				)
			),
			is_active=False,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_insert_pdf": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1", v1_urls_pdfs["view_pdf_insert_pdf"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_insert_pdf"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_merge_images": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1", v1_urls_pdfs["view_pdf_merge_images"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_merge_images"]
				)
			),
			is_active=True,
			other={
				"max_no_of_files": 20,
				"max_files_size_mb": 30,
			},
		),
	"view_pdf_merge_pdfs": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1",
				v1_urls_pdfs["view_pdf_merge_pdfs"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_merge_pdfs"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"max_no_of_files": 20,
				"max_files_size_mb": 30,
			},
		),
	"view_pdf_page_order": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1",
				v1_urls_pdfs["view_pdf_page_order"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_page_order"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_password_management_add": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1",
				v1_urls_pdfs["view_pdf_password_management"]["add"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_password_management"]["add"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_password_management_remove": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1",
				v1_urls_pdfs["view_pdf_password_management"]["remove"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_password_management"]["remove"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_password_management_change": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1",
				v1_urls_pdfs["view_pdf_password_management"]["change"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_password_management"]["change"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_rotate": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1", v1_urls_pdfs["view_pdf_rotate"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_rotate"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_split": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1", v1_urls_pdfs["view_pdf_split"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_split"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_watermark_text": CloudRunAPIEndpoint(
			api_url=join(
				"/pdf/v1",
				v1_urls_pdfs["view_pdf_watermark"]["text"].lstrip("/")
			),
			url_target=(
				urljoin(
					CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
					v1_urls_pdfs["view_pdf_watermark"]["text"]
				)
			),
			is_active=True,
			other={
				"media_type": ["application/pdf"],
				"file_size_mb": 30,
			},
		),
	"view_pdf_watermark_image": CloudRunAPIEndpoint(
		api_url=join(
			"/pdf/v1",
			v1_urls_pdfs["view_pdf_watermark"]["image"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_pdf_v1"]["base_url"],
				v1_urls_pdfs["view_pdf_watermark"]["image"]
			)
		),
		is_active=True,
		other={
			"pdf_media_type": ["application/pdf"],
			"image_media_type": ["image/png", "image/jpg", "image/jpeg"],
			"pdf_file_size_mb": 30,
			"image_file_size_mb": 1,
		},
	),
	"view_pdf_openai_openapi_json": CloudRunAPIEndpoint(
		api_url="/pdf/v1/openapi.json",
		url_target="",
		is_active=True,
	),
	"view_pdf_openai_well_known_manifest": CloudRunAPIEndpoint(
		api_url="/pdf/v1/.well-known/manifest.json",
		url_target="",
		is_active=True,
	)
}

excluded_urls_from_openai = [
	"view_pdf_openai_openapi_json",
	"view_pdf_openai_well_known_manifest",
	"view_pdf_password_management_remove",
	"view_pdf_password_management_change",
]

openai_extended_app_pdf_v1_urls = {}

for k, v in app_pdf_v1_urls.items():
	if k in excluded_urls_from_openai:
		continue
	v = copy.deepcopy(v)
	v.api_url = join(v.api_url, "openai")
	openai_extended_app_pdf_v1_urls[k+"_openai"] = v

# update the original dict
app_pdf_v1_urls.update(openai_extended_app_pdf_v1_urls)
