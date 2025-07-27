import os

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes


def setup_fastapi_tracing(app):
    service_name = "DoodleOps FastAPI App AI"
    resource = Resource(
        attributes={
            ResourceAttributes.SERVICE_NAME: service_name,
        }
    )
    provider = TracerProvider(resource=resource)

    if os.getenv('ENV_MODE') == 'local':
        otl_collector = os.getenv("OPENTELEMETRY_COLLECTOR_SERVICE_NAME")
        exporter = OTLPSpanExporter(
            endpoint=f"{otl_collector}:4317", insecure=True
        )
    else:
        exporter = CloudTraceSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
