from os.path import join
from urllib.parse import urljoin

from core.settings import CLOUD_RUN_APPs
from schemas.urls import CloudRunAPIEndpoint
from app_ai.cloud_run_container_app_ai.v1.views.urls import urls as v1_urls_ai


app_ai_v1_urls = {
	"twilio_whatsapp_webhook": CloudRunAPIEndpoint(
		api_url=join(
			"/ai/v1", v1_urls_ai["view_ai_twilio"].strip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_ai_v1"]["base_url"],
				v1_urls_ai["view_ai_twilio"].strip("/")
			)
		),
		is_active=True,
	),
}
