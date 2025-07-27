import importlib

from views.v1.route import v1_default_view_router

default_views = [
	"views.v1.view_user_credits",
]
for v in default_views:
	importlib.import_module(v)

app_docs_views = {
	"prefix": "app_docs",
	"fastapi_views":
		[
			"view_docs_excel_extract_each_sheet_to_new_excels",
			"view_docs_excel_merge",
			"view_excel_find_and_replace",
			"view_docs_excel_remove_empty_rows",
			"view_docs_excel_remove_rows_based_on_condition",
			"view_docs_excel_split",
		]
}
app_epub_views = {
	"prefix": "app_epub",
	"fastapi_views": ["view_epub_convert",]
}

app_html_views = {
	"prefix": "app_html",
	"fastapi_views": [
		"view_html_collect_performance_metrics_for_url",
		"view_html_convert_url_to_pdf",
	]
}

app_images_views = {
	"prefix": "app_images",
	"fastapi_views": [
		"view_image_compare_images",
		"view_image_convert_dicom_to_jpg",
		"view_image_convert_format",
		"view_image_convert_to_b_w",
		"view_image_convert_to_gray",
		"view_image_create_barcode",
		"view_image_gif_extract_frames",
		"view_image_create_gif",
		"view_image_create_ico",
		"view_image_create_qr_code",
		"view_image_create_thumbnail",
		"view_image_crop",
		"view_image_decode_qr_and_barcodes",
		"view_image_downsize",
		"view_image_remove_background",
		"view_image_ocr",
		"view_image_watermark_image",
		"view_image_watermark_text",
	]
}

app_pdf_views = {
	"prefix": "app_pdf",
	"fastapi_views": [
		"view_pdf_convert_to_image",
		"view_pdf_convert_to_word_pro",
		"view_pdf_delete_pages",
		"view_pdf_extract_images",
		"view_pdf_extract_tables",
		"view_pdf_insert_pdf",
		"view_pdf_merge_images",
		"view_pdf_merge_pdfs",
		"view_pdf_page_order",
		"view_pdf_password_management_add",
		"view_pdf_password_management_change",
		"view_pdf_password_management_remove",
		"view_pdf_rotate",
		"view_pdf_split",
		"view_pdf_watermark_image",
		"view_pdf_watermark_text",
	],
}

app_pdf_views["openai_views"] = app_pdf_views["fastapi_views"] + [
	"view_pdf_openai",
	"view_well_known_manifest_pdf",
]

app_ai_views = {
	"prefix": "app_ai",
	"fastapi_views": ["view_twilio_whatsapp_webhook",]
}

api_apps_view_routes = dict()

for app_views in [
	app_docs_views, app_epub_views, app_html_views, app_images_views,
	app_pdf_views, app_ai_views
]:
	for view in app_views["fastapi_views"]:
		view_module = importlib.import_module(
			f"{app_views['prefix']}.views.v1.fastapi_views.{view}"
		)

	for view in app_views.get("openai_views", []):
		try:
			view_module = importlib.import_module(
				f"{app_views['prefix']}.views.v1.openai_views.{view}"
			)
		except ModuleNotFoundError:
			pass

	fastapi_router_module = importlib.import_module(
		f"{app_views['prefix']}.views.v1.fastapi_views.route"
	)
	openai_router_module = importlib.import_module(
			f"{app_views['prefix']}.views.v1.openai_views.route"
		) if "openai_views" in app_views else None

	api_apps_view_routes[app_views["prefix"]] = {
		"fastapi_views": fastapi_router_module,
		"openai_views": openai_router_module
	}

# App Docs Routers
app_docs_routes = api_apps_view_routes["app_docs"]
v1_view_docs_router = app_docs_routes["fastapi_views"].v1_view_docs_router

# App Epub Routers
app_epub_routes = api_apps_view_routes["app_epub"]
v1_view_epub_router = app_epub_routes["fastapi_views"].v1_view_epub_router

# App Html Routers
app_html_routes = api_apps_view_routes["app_html"]
v1_view_html_router = app_html_routes["fastapi_views"].v1_view_html_router

# App Images Routers
app_images_routes = api_apps_view_routes["app_images"]
v1_view_images_router = app_images_routes["fastapi_views"].v1_view_images_router

# App PDF Routers
app_pdf_routes = api_apps_view_routes["app_pdf"]
v1_view_pdf_router = app_pdf_routes["fastapi_views"].v1_view_pdf_router
v1_view_pdf_router_openai = (
	app_pdf_routes["openai_views"].v1_view_pdf_router_openai
)

app_ai_routes = api_apps_view_routes["app_ai"]
v1_view_ai_router = app_ai_routes["fastapi_views"].v1_view_ai_router

__all__ = [
	# Default View Router
	"v1_default_view_router",

	# App Docs Routers
	"v1_view_docs_router",

	# App Epub Routers
	"v1_view_epub_router",

	# App Html Routers
	"v1_view_html_router",

	# App Images Routers
	"v1_view_images_router",

	# App PDF Routers
	"v1_view_pdf_router",

	# OpenAI PDF Routers
	"v1_view_pdf_router_openai",

	# App AI Routers
	"v1_view_ai_router",
]
