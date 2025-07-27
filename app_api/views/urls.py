from schemas.urls import CloudRunAPIEndpoint

default_urls = {
	"view_user_credits_v1": CloudRunAPIEndpoint(
		api_url="/user/v1/credits",
		url_target="",
		is_active=True,
	),
}
