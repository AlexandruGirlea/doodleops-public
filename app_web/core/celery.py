from __future__ import absolute_import, unicode_literals
import os

from celery import Celery

from core.tracing import setup_celery_tracing, OPENTELEMETRY_SERVICE_NAME

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

if OPENTELEMETRY_SERVICE_NAME:
	setup_celery_tracing()


app = Celery("core")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.beat_max_loop_interval = 60  # for celery beat

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
