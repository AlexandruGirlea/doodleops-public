from opentelemetry import trace
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from common.os_env_var_management import get_env_variable


ENV_MODE = get_env_variable("ENV_MODE")
OPENTELEMETRY_SERVICE_NAME = get_env_variable("OPENTELEMETRY_SERVICE_NAME")


class TracingServiceNames:
    django_run_server = "django-app-runserver"
    django_gunicorn = "django-app-gunicorn"
    celery_beat = "celery-beat"
    celery_worker = "celery-worker"


def setup_tracing(service_name, instrumentor, sampler: TraceIdRatioBased):
    # Set up the TracerProvider with a resource descriptor
    resource = Resource(attributes={
        ResourceAttributes.SERVICE_NAME: service_name,
    })

    if ENV_MODE == 'local':
        otl_collector = get_env_variable("OPENTELEMETRY_COLLECTOR_SERVICE_NAME")
        exporter = OTLPSpanExporter(endpoint=f"{otl_collector}:4317", insecure=True)
        sampler = TraceIdRatioBased(1.0)
    else:
        # Use Google Cloud Trace Exporter for GCP
        exporter = CloudTraceSpanExporter()

    provider = TracerProvider(resource=resource, sampler=sampler)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument the application
    instrumentor().instrument()


def setup_django_tracing():
    setup_tracing(
        service_name=TracingServiceNames.django_run_server,
        instrumentor=DjangoInstrumentor,
        sampler=TraceIdRatioBased(1.0)
    )


def setup_celery_tracing():
    if OPENTELEMETRY_SERVICE_NAME == TracingServiceNames.celery_beat:
        setup_tracing(
            service_name=TracingServiceNames.celery_beat,
            instrumentor=CeleryInstrumentor,
            sampler=TraceIdRatioBased(1.0)
        )
    elif OPENTELEMETRY_SERVICE_NAME == TracingServiceNames.celery_worker:
        setup_tracing(
            service_name=TracingServiceNames.celery_worker,
            instrumentor=CeleryInstrumentor,
            sampler=TraceIdRatioBased(0.2)
        )
