from os.path import join
from urllib.parse import urljoin

from core.settings import CLOUD_RUN_APPs
from schemas.urls import CloudRunAPIEndpoint
from app_docs.cloud_run_container_app_docs.v1.views.urls import (
	urls as v1_urls_docs
)

EXCEL_MEDIA_TYPE = (
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

app_docs_v1_urls = {
	"view_docs_excel_extract_each_sheet_to_new_excels": CloudRunAPIEndpoint(
		api_url=join(
			"/docs/v1",
			v1_urls_docs["excel"][
				"extract_each_sheet_to_new_excels"
			].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_app_docs_v1"]["base_url"],
				v1_urls_docs["excel"]["extract_each_sheet_to_new_excels"]
			)
		),
		is_active=True,
		other={"media_type": EXCEL_MEDIA_TYPE, "file_size_mb": 2},
	),
	"view_docs_excel_merge": CloudRunAPIEndpoint(
		api_url=join(
			"/docs/v1",
			v1_urls_docs["excel"]["merge"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_app_docs_v1"]["base_url"],
				v1_urls_docs["excel"]["merge"]
			)
		),
		is_active=True,
		other={
			"media_type": EXCEL_MEDIA_TYPE,
			"max_files_size_mb": 10,
			"max_number_of_files": 10,
		},
	),
	"view_docs_excel_remove_empty_rows": CloudRunAPIEndpoint(
		api_url=join(
			"/docs/v1",
			v1_urls_docs["excel"]["remove_empty_rows"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_app_docs_v1"]["base_url"],
				v1_urls_docs["excel"]["remove_empty_rows"]
			)
		),
		is_active=True,
		other={"media_type": EXCEL_MEDIA_TYPE, "file_size_mb": 2},
	),
	"view_docs_excel_remove_rows_based_on_condition": CloudRunAPIEndpoint(
		api_url=join(
			"/docs/v1",
			v1_urls_docs["excel"][
				"remove_rows_based_on_condition"
			].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_app_docs_v1"]["base_url"],
				v1_urls_docs["excel"]["remove_rows_based_on_condition"]
			)
		),
		is_active=True,
		other={"media_type": EXCEL_MEDIA_TYPE, "file_size_mb": 2},
	),
	"view_docs_excel_split": CloudRunAPIEndpoint(
		api_url=join(
			"/docs/v1",
			v1_urls_docs["excel"]["split"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_app_docs_v1"]["base_url"],
				v1_urls_docs["excel"]["split"]
			)
		),
		is_active=True,
		other={"media_type": EXCEL_MEDIA_TYPE, "file_size_mb": 2},
	),
	"view_excel_find_and_replace": CloudRunAPIEndpoint(
		api_url=join(
			"/docs/v1",
			v1_urls_docs["excel"]["find_and_replace"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_app_docs_v1"]["base_url"],
				v1_urls_docs["excel"]["find_and_replace"]
			)
		),
		is_active=True,
		other={"media_type": EXCEL_MEDIA_TYPE, "file_size_mb": 2},
	)
}
