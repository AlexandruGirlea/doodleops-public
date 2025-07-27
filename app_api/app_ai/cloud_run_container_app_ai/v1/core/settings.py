import os
import ast
import json
import logging

from google.cloud import secretmanager

logger = logging.getLogger("APP_AI_V1_"+__name__)

ENV_MODE = os.getenv("ENV_MODE")
SECRET_MANAGER_NAME = os.getenv("SECRET_MANAGER_NAME")
EVENTARC_SERVICE_ACCOUNT = os.getenv("EVENTARC_SERVICE_ACCOUNT")  # for auth
REDIS_KEY_TTL_MAX = 60 * 60 * 24 * 31 * 6  # 6 months
MAX_NUMBER_OF_HISTORY_MSGS = 20  # both user and AI msgs
MAX_NUMBER_OF_HISTORY_MSGS_PERPLEXITY = 6  # both user and AI msgs


if ENV_MODE != "local":
	project_id = os.getenv("GCP_PROJECT_ID")
	if not project_id:
		msg = "GCP_PROJECT_ID not set"
		logger.error(msg)
		raise ValueError(msg)
	
	secret_name = SECRET_MANAGER_NAME + "/versions/latest"

	client = secretmanager.SecretManagerServiceClient()
	response = client.access_secret_version(request={"name": secret_name})

	if response.payload.data:
		secrets_json = json.loads(response.payload.data.decode('UTF-8'))
		for k, v in secrets_json.items():
			os.environ[k] = str(v)
	else:
		msg = "No data found in secret"
		logger.error(msg)
		raise ValueError(msg)

MAX_FILE_SIZES_MB_BY_TYPE = {
	"image/jpeg": 5, "image/jpg": 5, "image/png": 5,
	"audio/mp3": 2, "audio/vnd.wave": 2, "audio/ogg": 2,
	"application/pdf": 5,
}

MAX_PDF_PAGES = 10
MAX_TEXT_LENGTH_TO_TRANSLATE_FOR_AUDIO_RESPONSE = 1000  # characters
MAX_TEXT_LENGTH_TO_TRANSLATE_FOR_TEXT_RESPONSE = 2000  # characters


ALLOWED_FILE_FORMATS = {
	"image": ('jpeg', 'jpg', 'png'),
	"audio": ('mp3', 'flac', 'ogg'),
	"application": ('pdf',),
}

MAX_AUDIO_LENGTH_SECONDS = 59  # seconds
ERROR_AUDIO_LENGTH = "Audio length has to be under 1 minute."

COUNTRY_PHONE_CODES_AND_LANGUAGES = {
	"+44": "en",  # UK
	"+33": "fr",  # France
	"+40": "ro",  # Romania
	"+49": "de",  # Germany
	"+34": "es",  # Spain
	"+39": "it",  # Italy
	"+351": "pt",  # Portugal
	"+81": "ja",  # Japan
	"+91": "in",  # India
	"+30": "el",  # Greece
	"+1": "en",  # US
}

GENERIC_NO_ACCOUNT_ERROR_MSG = {
	"en": (
		"Please create an account first on https://doodleops.com/login to continue. "
		"\nIf you already have an account, please add this phone number by going to "
		"https://doodleops.com/profile/personal-information/"
	),
	"fr": (
		"Veuillez d'abord créer un compte sur https://doodleops.com/login pour "
		"continuer. \nSi vous possédez déjà un compte, veuillez ajouter ce numéro "
		"de téléphone en vous rendant sur: "
		"https://doodleops.com/profile/personal-information/"
	),
	"ro": (
		"Vă rugăm să creați mai întâi un cont pe https://doodleops.com/login pentru "
		"a continua. \nDacă aveți deja un cont, vă rugăm să adăugați acest număr de "
		"telefon mergând la: https://doodleops.com/profile/personal-information/"
	),
	"de": (
		"Bitte erstellen Sie zunächst ein Konto auf https://doodleops.com/login, um "
		"fortzufahren. \nWenn Sie bereits ein Konto haben, fügen Sie bitte diese "
		"Telefonnummer hinzu, indem Sie zu "
		"https://doodleops.com/profile/personal-information/ gehen."
	),
	"es": (
		"Por favor, cree una cuenta primero en https://doodleops.com/login para "
		"continuar. \nSi ya tiene una cuenta, agregue este número de teléfono yendo a "
		"https://doodleops.com/profile/personal-information/"
	),
	"it": (
		"Si prega di creare prima un account su https://doodleops.com/login per "
		"continuare. \nSe si dispone già di un account, aggiungere questo numero di "
		"telefono andando su https://doodleops.com/profile/personal-information/"
	),
	"pt": (
		"Por favor, crie uma conta primeiro em https://doodleops.com/login para "
		"continuar. \nSe já tiver uma conta, adicione este número de telefone indo "
		"para https://doodleops.com/profile/personal-information/"
	),
	"ja": (
		"続行するには、最初にhttps://doodleops.com/loginでアカウントを作成してください。 "
		"すでにアカウントをお持ちの場合は、https://doodleops.com/profile/personal-information/ に移動してこの電話番号を追加してください。"
	),
	"in": (
		"कृपया जारी रखने के लिए सबसे पहले https://doodleops.com/login पर एक खाता बनाएं। "
		"यदि आपके पास पहले से एक खाता है, तो कृपया इस फोन नंबर को जोड़ने के लिए "
		"https://doodleops.com/profile/personal-information/ पर जाएं।"
	),
	"el": (
		"Παρακαλώ δημιουργήστε πρώτα ένα λογαριασμό στο https://doodleops.com/login "
		"για να συνεχίσετε. \nΕάν έχετε ήδη λογαριασμό, προσθέστε αυτόν τον αριθμό "
		"τηλεφώνου πηγαίνοντας στο https://doodleops.com/profile/personal-information/"
	),
}

GENERIC_RECURSION_ERROR_MSG = (
	"Sorry, I am unable to process your message at the moment. Please try to be "
	"more specific."
)

GENERIC_ERROR_MSG_CONTACT_SUPPORT = (
	"Sorry, I am unable to process your message at the moment. "
	"If the problem persists, please contact support: "
	"https://doodleops.com/contact/"
)

GENERIC_ERROR_MEDIA_FILE_MSG = (
	"Sorry, I am unable to process the media file at the moment."
)

SPECIFIC_IMAGE_ERROR_MSG = (
		"For images, please only upload JPEG, JPG, or PNG files, under "
		f"{MAX_FILE_SIZES_MB_BY_TYPE.get('image/jpeg')} MB."
	)

SPECIFIC_AUDIO_ERROR_MSG = (
	"Please only upload WhatsApp voice recordings, under 2 minutes long."
)
	

SPECIFIC_ERROR_MEDIA_FILE_MSG = {
	"application/pdf": (
		"Please only upload PDF files under "
		f"{MAX_FILE_SIZES_MB_BY_TYPE.get('application/pdf')} MB and "
		f"with max {MAX_PDF_PAGES} pages."
	),
	"image/jpeg": SPECIFIC_IMAGE_ERROR_MSG,
	"image/jpg": SPECIFIC_IMAGE_ERROR_MSG,
	"image/png": SPECIFIC_IMAGE_ERROR_MSG,
	"audio/mp3": SPECIFIC_AUDIO_ERROR_MSG,
	"audio/vnd.wave": SPECIFIC_AUDIO_ERROR_MSG,
	"audio/ogg": SPECIFIC_AUDIO_ERROR_MSG,
}

NOT_ENOUGH_CREDITS_MSG = (
	"Sorry, you do not have enough credits to make this request. "
	"Please visit https://doodleops.com/financial/pricing-credits/ to "
	"purchase more credits."
)

LIST_OF_SERVICES_WE_PROVIDE = ", ".join((
	"shopping assistance", "career advice", "stock market information",
	"image generation",
	" The user can also ask for support, report a bug, provide feedback on these "
	"services or suggest a new feature that they might want to see in the future."
))

LIST_OF_MEDIA_INTERPRETER_SERVICES = """
Based on the type of media file the user uploads, we can help with the following:
- image media file: plant advice, animal advice, object recognition,
solve math problems if image contains a math problems, answer quizzes if image
contains a quiz / test, search for similar images online and return links,
judge attractiveness of a person, suggest meals based on the image,
translate text in the image in the desired language,
try to identify person, object or place in the image, suggest fashion style
based on how a person is dressed in the image, suggest a haircuts,
diy project ideas based on the image, instructions how to fix something based
on the image, general image description, and more.
- pdf media: for summarizing the content, CV review, or finding information in
the document. We can't help with document editing currently.
- audio media: understand the audio content and translate it, respond with audio
content that was translated.
"""

MEDIA_FILE_HUMAN_MSG_FORMAT = (
	" media link: {media_file_link}, mime type: {file_content_type}."
)

# ------------ REDIS start
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB_DEFAULT = os.getenv("REDIS_DB_DEFAULT")
# ------------ REDIS end

# ------------ Twilio start
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
# ------------ Twilio end

# ------------ LANGCHAIN start
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
# ------------ LANGCHAIN end

# ------------ AI SERVICES start
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
# ------------ AI SERVICES end


# ------------ ZENDESK start
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
ZENDESK_USER_EMAIL = os.getenv("ZENDESK_USER_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
ZENDESK_GROUP_SETTINGS_KEY = ast.literal_eval(
	os.getenv("ZENDESK_GROUP_SETTINGS_KEY")
)
# ------------ ZENDESK end

# ------------ TEMP Bucket
TEMP_API_FILES_BUCKET = os.getenv("TEMP_API_FILES_BUCKET")
BUKET_BASE_URL = os.getenv("BUKET_BASE_URL")
BUKET_GCP_URL = os.getenv("BUKET_GCP_URL")
# ------------ TEMP Bucket end

# ------------ VertexAI GCP
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION")
# ------------ VertexAI GCP end

# ------------ Google Custom Search
CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
GCP_CUSTOM_SEARCH_API_KEY = os.getenv("GCP_CUSTOM_SEARCH_API_KEY")
# ------------ Google Custom Search end
