import multiprocessing

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from common.os_env_var_management import get_env_variable

PORT = get_env_variable("PORT", "8080")
ENV_MODE = get_env_variable("ENV_MODE")
if not ENV_MODE:
    raise ValueError("ENV_MODE environment variable not set")

bind = f"0.0.0.0:{PORT}"

if ENV_MODE == "local":
    workers = 1
else:
    workers = multiprocessing.cpu_count() * 2

worker_class = "sync"
worker_connections = 1000

timeout = 60
keepalive = 2

errorlog = "-"
accesslog = "-"
access_log_format = (
    '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
)

if ENV_MODE == "local":
    loglevel = "debug"
    reload = True
else:
    loglevel = "info" if ENV_MODE == "prod" else "debug"
    reload = False


def post_fork(server, worker):
    """
    This function is called just after a worker has been forked so that all
    calls can be traced.
    """
    server.log.info("Worker spawned (pid: %s)", worker.pid)

    resource = Resource.create(
        attributes={
            "service.name": "django-app-gunicorn",
            "worker": worker.pid,
        }
    )
    if ENV_MODE == 'local':
        otl_collector = get_env_variable("OPENTELEMETRY_COLLECTOR_SERVICE_NAME")
        exporter = OTLPSpanExporter(
            endpoint=f"http://{otl_collector}:4317", insecure=True
        )
        sampler = TraceIdRatioBased(1.0)
    else:
        # Use Google Cloud Trace Exporter for GCP
        exporter = CloudTraceSpanExporter()
        # sample 1 in every 1000 traces
        sampler = TraceIdRatioBased(1 / 1000)

    trace.set_tracer_provider(
        TracerProvider(resource=resource, sampler=sampler)
    )
    span_processor = BatchSpanProcessor(exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
