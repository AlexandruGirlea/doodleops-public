"""
In GCP Cloud we need to enable the Google Drive API
https://console.cloud.google.com/apis/api/drive.googleapis.com/metrics
"""

import io
import os
import logging
import tempfile
from datetime import datetime
from http import HTTPStatus

import redis.asyncio as redis
from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from core import settings
from core.urls import urls
from schemas.auth import TokenData
from schemas.urls import ExternalAPIEndpoint
from common.other import generate_unique_filename, cleanup_temp_dir
from common.file_validation import validate_file_size_mb, validate_file_type
from common.cost_management import cost_setup, cost_teardown
from common.redis_utils import set_user_api_call_lock, release_user_api_call_lock


APP_NAME, VERSION, API = "app_pdf", "v1", "view_pdf_convert_to_word_pro"
API_NAME = "/".join([APP_NAME, VERSION, API])
URL_DATA: ExternalAPIEndpoint = urls[APP_NAME][VERSION][API]

logger = logging.getLogger("APP_API_"+API_NAME+__name__)

EXPORT_MEDIA_TYPE = (
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


async def get_response(
		token_data: TokenData, redis_conn: redis.Redis, file: UploadFile,
):
	validate_file_type(
		file=file, file_extensions=('pdf',),
		content_type=tuple(URL_DATA.other["media_type"]),
	)

	date_time_now = datetime.now()
	current_date = datetime.now().strftime("%d-%m-%Y")
	timestamp = int(date_time_now.timestamp())
	temp_dir = tempfile.mkdtemp()

	try:
		await set_user_api_call_lock(
			redis_conn=redis_conn, username=token_data.username, api_name=API_NAME
		)

		await validate_file_size_mb(
			file=file,
			max_size_mb=URL_DATA.other["file_size_mb"]
		)

		api_cost, is_metered = await cost_setup(
			redis_conn=redis_conn,
			username=token_data.username,
			api_name=API_NAME,
			current_date=current_date,
		)

		unique_filename = generate_unique_filename(extension=".pdf")

		pdf_path = os.path.join(temp_dir, unique_filename)

		with open(pdf_path, "wb") as f:
			f.write(await file.read())

		creds = Credentials.from_service_account_info(
			settings.GCF_SERVICE_ACCOUNT_JSON,
			scopes=['https://www.googleapis.com/auth/drive'],
		)
		service = build('drive', 'v3', credentials=creds, cache_discovery=False)

		file_metadata = {
			'name': unique_filename.replace('.pdf', ''),
			# Set the MIME type to Google Docs
			'mimeType': 'application/vnd.google-apps.document'
		}

		media = MediaFileUpload(
			pdf_path, mimetype='application/pdf', resumable=True
		)

		gfile = service.files().create(
			body=file_metadata, media_body=media, fields='id'
		).execute()

		file_id = gfile.get('id')

		request = service.files().export_media(
			fileId=file_id,
			mimeType=EXPORT_MEDIA_TYPE
		)

		fh = io.BytesIO()
		downloader = MediaIoBaseDownload(fh, request)

		while True:
			status, done = downloader.next_chunk()
			if done:
				break
		unique_filename_docx = unique_filename.lower().replace('.pdf', '.docx')
		docx_path = os.path.join(temp_dir, unique_filename_docx)
		with open(docx_path, 'wb') as f:
			fh.seek(0)
			f.write(fh.read())

		service.files().delete(fileId=file_id).execute()

		resp = FileResponse(
			path=docx_path,
			filename=file.filename.lower().replace('.pdf', '.docx'),
			media_type=EXPORT_MEDIA_TYPE,
			status_code=HTTPStatus.OK.value
		)

		final_resp = await cost_teardown(
			redis_conn=redis_conn,
			resp_type="file",
			resp=resp,
			username=token_data.username,
			api_name=API_NAME,
			api_cost=api_cost,
			current_date=current_date,
			timestamp=timestamp,
			is_metered=is_metered,
		)
		return {
			"resp": final_resp, "temp_dir": temp_dir,
			"temp_file": unique_filename_docx
		}

	except Exception as e:
		logger.error(f"Error converting PDF to Word: {str(e)}")
		cleanup_temp_dir(temp_dir=temp_dir)
		raise HTTPException(
			status_code=500,
			detail=(
				"Could not converting PDF to Word, if error persists "
				"please contact support."
			)
		)

	finally:
		await release_user_api_call_lock(
			redis_conn=redis_conn, username=token_data.username, api_name=API_NAME
		)
