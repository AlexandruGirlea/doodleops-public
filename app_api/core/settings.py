import os
import json
from pathlib import Path

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from common.secrets_manager import set_app_api_secrets

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_MODE = os.getenv("ENV_MODE")
if not ENV_MODE:
	raise ValueError("ENV_MODE environment variable not set")

HYPER_TEXT_PROTOCOL = "http"

if ENV_MODE != "local":
	HYPER_TEXT_PROTOCOL = "https"
	set_app_api_secrets()

GENERIC_ERROR_MSG = (
	"Something went wrong. If the problem persists, please contact support."
)
NOT_ENOUGH_CREDITS_MSG = (
	"Sorry, you do not have enough credits to make this request. "
	"Please visit https://doodleops.com/financial/pricing-credits/ to "
	"purchase more credits."
)

ALLOW_ORIGINS = os.environ.get("ALLOW_ORIGINS").split(",")
ALLOW_METHODS = os.environ.get("ALLOW_METHODS").split(",")
ALLOW_HEADERS = os.environ.get("ALLOW_HEADERS").split(",")

API_COST_BAD_REQUEST = 0

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL")

GCF_SERVICE_ACCOUNT_JSON = json.loads(
	os.getenv("GCF_SERVICE_ACCOUNT_JSON").replace("'", '"')
)

# ------------ API FILE EXTENSIONS start
FILE_EXTENSIONS_v1_image_to_black_and_white = ["jpg", "jpeg", "png"]
FILE_EXTENSIONS_v1_openai_v4o_vision = ["jpg", "jpeg", "png"]
FILE_EXTENSIONS_v1_pdf_to_word_pro = ["pdf", ]
# ------------ API TYPES end

# ------------ API FILE SIZE LIMITS start
MAX_SIZE_MB_v1_image_to_black_and_white = 20
MAX_SIZE_MB_v1_openai_v4o_vision = 2
# ------------ API FILE SIZE LIMITS end

# ------------ DB start
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")

DB_Base = declarative_base()
DATABASE_URL = (
	f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
	f"{MYSQL_DATABASE}"
)

if ENV_MODE in {"prod", "dev"}:  # this is required for the Google Cloud SQL
	DATABASE_URL = DATABASE_URL.replace("mysql", "mysql+pymysql")

engine = create_engine(
	DATABASE_URL,
	echo=True,
	pool_recycle=3600,      # Recycle connections after 1 hour
	pool_pre_ping=True      # Check connection validity before using it
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
DB_Base.metadata.create_all(bind=engine)
# ------------ DB end

# ------------ REDIS start
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB_DEFAULT = os.getenv("REDIS_DB_DEFAULT")
# ------------ REDIS end

# ------------ CRYPTO start
CRYPT_SECRET_KEY_WEB = os.getenv("CRYPT_SECRET_KEY_WEB")
CRYPT_SECRET_KEY_G_CLOUD_RUN = os.getenv("CRYPT_SECRET_KEY_G_CLOUD_RUN")
EXPECTED_TOKEN_CLOUD_RUN = os.getenv("EXPECTED_TOKEN_CLOUD_RUN")
# ------------ CRYPTO end

# ------------ OpenAI start
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# ------------ OpenAI end

# ------------ CLOUD RUN APPs start

APP_DOCS_V1_URL = os.getenv("APP_DOCS_V1_URL", "app_docs_v1")
APP_EPUB_V1_URL = os.getenv("APP_EPUB_V1_URL", "app_epub_v1")
APP_IMAGES_V1_URL = os.getenv("APP_IMAGES_V1_URL", "app_images_v1")
APP_PDF_V1_URL = os.getenv("APP_PDF_V1_URL", "app_pdf_v1")
APP_AI_V1_URL = os.getenv("APP_AI_V1_URL", "app_ai_v1")

CLOUD_RUN_APPs = {
	"cloud_run_app_docs_v1": {
		"base_url": f"{HYPER_TEXT_PROTOCOL}://{APP_DOCS_V1_URL}",
	},
	"cloud_run_epub_v1": {
		"base_url": f"{HYPER_TEXT_PROTOCOL}://{APP_EPUB_V1_URL}",
	},
	"cloud_run_images_v1": {
		"base_url": f"{HYPER_TEXT_PROTOCOL}://{APP_IMAGES_V1_URL}",
	},
	"cloud_run_pdf_v1": {
		"base_url": f"{HYPER_TEXT_PROTOCOL}://{APP_PDF_V1_URL}",
	},
	"cloud_run_ai_v1": {
		"base_url": f"{HYPER_TEXT_PROTOCOL}://{APP_AI_V1_URL}",
	},
}

if ENV_MODE == "local":
	for key in CLOUD_RUN_APPs.keys():
		CLOUD_RUN_APPs[key][
			"base_url"] = f"{CLOUD_RUN_APPs[key]['base_url']}:8080"
# ------------ CLOUD RUN APPs end

# ------------ LANGUAGE CODES start
with open(
		BASE_DIR.joinpath(
			'app_images/cloud_run_container_app_images/v1/utils/iso_639-languages.json'
		)
) as f:
	ISO_LANGUAGES = []
	raw_iso_languages = json.load(f)
	for value in raw_iso_languages.values():
		ISO_LANGUAGES.append((value['639-2'], value['name']))
# ------------ LANGUAGE CODES end

# ------------ TEMP Bucket
TEMP_API_FILES_BUCKET = os.getenv("TEMP_API_FILES_BUCKET")
BUKET_BASE_URL = os.getenv("BUKET_BASE_URL")
# ------------ TEMP Bucket end

# ------------ Twilio
COUNTRY_CODE_PHONE_RESTRICTION = os.getenv(
	"COUNTRY_CODE_PHONE_RESTRICTION",
	"+44,+40,+33,+49,+34,+39,+351,+81,+91,+30,+1,+966"
)

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

MAX_MSGS_PER_MINUTE = 5
MAX_MSGS_PER_HOUR = 60

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
# ------------ Twilio end

# ------------ OpenAPI and Hide private API paths
ENDS_WITH_OPENAI = "/openai"
HIDE_PRIVATE_API_PATHS = (
	"/user/v1/credits",
	"/pdf/v1/openapi.json",
	"/pdf/v1/.well-known/manifest.json",
	"/ai/v1/twilio-events/dispatch"
)
with open("templates/ReDoc.html") as f:
	RE_DOC_HTML = f.read()
# ------------ OpenAPI end
