from django.conf import settings
from django.core.exceptions import ValidationError
from google.oauth2 import service_account
from google.cloud import recaptchaenterprise_v1

DEFAULT_RECAPTCHA_ACTION = 'submit'
GENERIC_RECAPTCHA_ERROR = (
	"reCAPTCHA verification failed. Please try again. If you are not a bot, "
	f"and the issue persists, please contact us at "
	f"{settings.DEFAULT_SUPPORT_EMAIL}"
)


def create_recaptcha_assessment(
		project_id, recaptcha_key, token
) -> recaptchaenterprise_v1.Assessment:
	credentials = service_account.Credentials.from_service_account_info(
		settings.GOOGLE_SERVICE_ACCOUNT_KEY_JSON
	)

	client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient(
		credentials=credentials
	)

	# Build the event object
	event = recaptchaenterprise_v1.Event()
	event.site_key = recaptcha_key
	event.token = token

	assessment = recaptchaenterprise_v1.Assessment()
	assessment.event = event
	project_name = f"projects/{project_id}"

	request = recaptchaenterprise_v1.CreateAssessmentRequest()
	request.assessment = assessment
	request.parent = project_name

	return client.create_assessment(request)


def validate_recaptcha(request, recaptcha_action=DEFAULT_RECAPTCHA_ACTION):
	if request.method != 'POST':
		raise ValidationError("Only POST requests are allowed.")

	token = request.POST.get('g-recaptcha-response')

	if not token:
		raise ValidationError(GENERIC_RECAPTCHA_ERROR)

	response = create_recaptcha_assessment(
		project_id=settings.GOOGLE_PROJECT_ID,
		recaptcha_key=settings.RECAPTCHA_PUBLIC_KEY,
		token=token
	)

	token_properties = response.token_properties

	if not token_properties.valid:
		raise ValidationError(GENERIC_RECAPTCHA_ERROR)

	elif token_properties.action != recaptcha_action:
		raise ValidationError(GENERIC_RECAPTCHA_ERROR)

	elif response.risk_analysis.score < settings.RECAPTCHA_REQUIRED_SCORE:
		raise ValidationError(GENERIC_RECAPTCHA_ERROR)

	return True


