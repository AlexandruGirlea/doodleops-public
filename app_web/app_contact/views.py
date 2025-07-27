import logging

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError

from app_api.models import API
from app_contact.models import TYPE
from app_contact.forms import ContactForm
from app_settings.utils import get_setting
from common.recaptcha_logic import validate_recaptcha


logger = logging.getLogger(__name__)

GENERIC_RECAPTCHA_ERROR = (
	"reCAPTCHA verification failed. Please try again. If you are not a bot, "
	f"and the issue persists, please contact us at "
	f"{settings.DEFAULT_SUPPORT_EMAIL}"
)


def contact(request):
	form = ContactForm()

	if request.method == 'POST':
		form = ContactForm(request.POST)

		try:
			validate_recaptcha(request)
		except ValidationError as e:
			messages.error(request, e.message)
			return redirect('contact')

		if form.is_valid():
			if request.user.is_authenticated:
				form.instance.user = request.user
				form.instance.email = request.user.email

			if form.data.get('api_unique_id'):
				form.instance.api = API.objects.get(
					unique_id=form.data.get('api_unique_id')
				)
			form.save()
			messages.success(
				request, 'Your message has been sent successfully.'
			)
			return redirect('contact')
		else:
			messages.error(request, 'Please correct the errors below.')

	api_unique_id = request.GET.get('api-feedback', '')
	api = None
	if api_unique_id:
		try:
			api = API.objects.get(unique_id=api_unique_id)
		except API.DoesNotExist:
			pass
	return render(
		request=request,
		template_name='contact.html',
		context={
			'api_unique_id': api_unique_id,
			"api_name": api.display_name if api else None,
			"contact_types": TYPE,
			"calendly_url": get_setting('calendly_url'),
			"recaptcha_public_key": settings.RECAPTCHA_PUBLIC_KEY,
			"form": form
		}
	)
