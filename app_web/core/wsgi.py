import os

from django.core.wsgi import get_wsgi_application
from opentelemetry.instrumentation.django import DjangoInstrumentor

from core.tracing import (
	OPENTELEMETRY_SERVICE_NAME, TracingServiceNames, setup_django_tracing
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

if OPENTELEMETRY_SERVICE_NAME:
	if OPENTELEMETRY_SERVICE_NAME == TracingServiceNames.django_run_server:
		setup_django_tracing()
	elif OPENTELEMETRY_SERVICE_NAME == TracingServiceNames.django_gunicorn:
		DjangoInstrumentor().instrument()

application = get_wsgi_application()
