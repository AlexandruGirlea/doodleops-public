from fastapi import Request, Depends

from core.urls import urls
from core.settings import ENV_MODE
from schemas.urls import CloudRunAPIEndpoint
from schemas.redis_db import REDIS_KEY_API_COST
from app_pdf.views.v1.openai_views.route import v1_view_pdf_router_openai
from app_pdf.cloud_run_container_app_pdf.v1.views.urls import (
	urls as cloud_run_urls,
)
from common.redis_utils import get_redis_conn
from views.urls import default_urls
from common.other import clean_openapi_schemas

APP_NAME, VERSION, API = "app_pdf", "v1", "view_pdf_openai_openapi_json"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: CloudRunAPIEndpoint = urls[APP_NAME][VERSION][API]

# Excluded API paths because of OpenAI limitations
TO_EXCLUDE = [
	cloud_run_urls.get("view_pdf_password_management").get("remove"),
	cloud_run_urls.get("view_pdf_password_management").get("change")
]

TO_ALLOW = [
	default_urls.get("view_user_credits_v1").api_url
]


@v1_view_pdf_router_openai.get(URL_DATA.api_url, include_in_schema=True)
async def v1_view_openapi_pdf(
		request: Request,
		redis_conn=Depends(get_redis_conn)
):
	openapi_schema = request.app.openapi()
	allowed_prefix = "/pdf/v1"
	allowed_suffix = "/openai"
	openapi_schema['info']['summary'] = (
		"These are the endpoints for the PDF Actions on DoodleOps."
	)

	# Filter paths
	filtered_paths = {}
	for path, methods in openapi_schema.get("paths", {}).items():
		for i in TO_ALLOW:
			if path == i:
				filtered_paths[path] = methods

		if path.startswith(allowed_prefix) and path.endswith(allowed_suffix):
			jump_over_url = False
			for e in TO_EXCLUDE:
				if e in path:
					jump_over_url = True
					break
			if jump_over_url:
				continue
			filtered_paths[path] = methods

	# we add the cost in the description of the endpoint
	price_correlation_dict = {}
	for k in urls["app_pdf"]["v1"]:
		key = REDIS_KEY_API_COST.format(api_name="app_pdf/v1/" + k)

		try:
			api_price = await redis_conn.get(key)
		except:
			api_price = None

		if urls["app_pdf"]["v1"][k].is_active and api_price:

			price_correlation_dict["app_pdf/v1/" + k] = {
				"url": urls["app_pdf"]["v1"][k].api_url + "/openai",
				"api_price": int(api_price) if api_price else None,
			}
	for k, v in price_correlation_dict.items():
		try:
			api_cost_msg = (
				f" Cost: {v.get('api_price')} credits."
				if isinstance(v.get("api_price"), int)
				else (
					" Cost: Not available. Please visit DoodleOps.com to check "
					"the cost."
				)
			)
			filtered_paths[v.get("url")]["post"]["description"] += api_cost_msg
		except Exception as e:
			pass

	openapi_schema["paths"] = filtered_paths

	pruned_schemas = clean_openapi_schemas(
		openapi_schema=openapi_schema,
		filtered_paths=filtered_paths,
	)

	if ENV_MODE != "local":
		request.base_url._url = request.base_url._url.replace(
			"http://", "https://"
		)

	openapi_schema["components"]["schemas"] = pruned_schemas
	openapi_schema["servers"] = [{"url": request.base_url._url}]
	return openapi_schema
