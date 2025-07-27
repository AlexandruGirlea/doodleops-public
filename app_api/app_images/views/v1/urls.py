from os.path import join
from urllib.parse import urljoin

from core.settings import CLOUD_RUN_APPs
from schemas.urls import CloudRunAPIEndpoint
from app_images.cloud_run_container_app_images.v1.views.urls import (
	urls as v1_urls_images
)

app_images_v1_urls = {
	"view_image_rotate": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["general"]["rotate"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["general"]["rotate"]
			)
		),
		is_active=False,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png", "image/gif"],
			"file_size_mb": 10
		},
	),
	"view_image_crop": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["general"]["crop"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["general"]["crop"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png", "image/gif"],
			"file_size_mb": 10
		},
	),
	"view_image_ocr": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["general"]["ocr"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["general"]["ocr"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_compare_images": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1",
			v1_urls_images["general"]["compare_images"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["general"]["compare_images"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_create_thumbnail": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["create"]["thumbnail"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["create"]["thumbnail"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_create_ico": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["create"]["ico"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["create"]["ico"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_create_qr_code": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1",
			v1_urls_images["read_codes"]["create_qr_code"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["read_codes"]["create_qr_code"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/png"],
			"file_size_mb": 2,
		},
	),
	"view_image_create_barcode": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1",
			v1_urls_images["read_codes"]["create_barcode"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["read_codes"]["create_barcode"]
			)
		),
		is_active=True,
		other={},
	),
	"view_image_decode_qr_and_barcodes": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1",
			v1_urls_images["read_codes"]["decode_qr_and_barcodes"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["read_codes"]["decode_qr_and_barcodes"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_create_gif": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["gif"]["create"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["gif"]["create"]
			)
		),
		is_active=True,
		other={
			"media_type": [
				"image/jpeg", "image/jpg", "image/png", "video/mp4",
				"video/avi", "video/mov"
			],
			"file_size_mb": 10,
		},
	),
	"view_image_gif_extract_frames": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["gif"]["extract_frames"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["gif"]["extract_frames"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/gif"],
			"file_size_mb": 10,
		},
	),
	"view_image_downsize": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1",
			v1_urls_images["image_manipulation"]["downsize"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["image_manipulation"]["downsize"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 30,
		},
	),
	"view_image_cartoonify": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1",
			v1_urls_images["image_manipulation"]["cartoonify"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["image_manipulation"]["cartoonify"]
			)
		),
		is_active=False,  # This endpoint is currently inactive, still in development
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_remove_background": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1",
			v1_urls_images[
				"image_manipulation"
			]["remove_background"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["image_manipulation"]["remove_background"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_watermark_text": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["watermark"]["add_text"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["watermark"]["add_text"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"font_media_type": [
				"font/ttf", "font/otf", "application/octet-stream",
			],
			"background_file_size_mb": 10,
			"font_file_size_mb": 2,
			"text_max_length": 25
		},
	),
	"view_image_watermark_image": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["watermark"]["add_image"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["watermark"]["add_image"]
			)
		),
		is_active=True,
		other={
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
			"file_size_mb": 10
		},
	),
	"view_image_convert_to_b_w": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["convert"]["to_b_w"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["convert"]["to_b_w"]
			)
		),
		is_active=True,
		other={
			"file_size_mb": 30,
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
		},
	),
	"view_image_convert_to_gray": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["convert"]["to_gray"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["convert"]["to_gray"]
			)
		),
		is_active=True,
		other={
			"file_size_mb": 30,
			"media_type": ["image/jpeg", "image/jpg", "image/png"],
		},
	),
	"view_image_convert_dicom_to_jpg": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["convert"]["dicom_to_img"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["convert"]["dicom_to_img"]
			)
		),
		is_active=True,
		other={
			"file_size_mb": 30,
			"media_type": ["application/dicom"],
		},
	),
	"view_image_convert_format": CloudRunAPIEndpoint(
		api_url=join(
			"/images/v1", v1_urls_images["convert"]["format"].lstrip("/")
		),
		url_target=(
			urljoin(
				CLOUD_RUN_APPs["cloud_run_images_v1"]["base_url"],
				v1_urls_images["convert"]["format"]
			)
		),
		is_active=True,
		other={
			"file_size_mb": 30,
		},
	),
}
