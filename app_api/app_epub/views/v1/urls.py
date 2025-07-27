from os.path import join
from urllib.parse import urljoin

from core.settings import CLOUD_RUN_APPs
from schemas.urls import CloudRunAPIEndpoint
from app_epub.cloud_run_container_app_epub.v1.views.urls import (
	urls as v1_urls_epub
)

app_epub_v1_urls = {
	"view_epub_convert": CloudRunAPIEndpoint(
		api_url=join(
			"/epub/v1", v1_urls_epub["convert_format"]["convert"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_epub_v1"]["base_url"],
				v1_urls_epub["convert_format"]["convert"]
			)
		),
		is_active=False,
		other={"file_size_mb": 10},
	),
}
