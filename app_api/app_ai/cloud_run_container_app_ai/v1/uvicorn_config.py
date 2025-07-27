import os
import json
import logging
import multiprocessing
from datetime import datetime, timezone

import uvicorn


FASTAPI_APP = "core.fastapi_app:app"
PORT = os.getenv("PORT", "8080")
HOST = os.getenv("HOST", "0.0.0.0")
ENV_MODE = os.getenv("ENV_MODE")

if not ENV_MODE:
    raise ValueError("ENV_MODE environment variable not set")


def sanitize_for_json(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    else:
        return str(obj)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": (
                datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat()
            ),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
        }

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        excluded_keys = [
            "asctime", "created", "filename", "funcName", "levelname", "levelno",
            "msecs", "module", "msg", "name", "process", "processName",
            "relativeCreated", "thread", "threadName"
        ]

        extra_fields = {
            k: v for k, v in record.__dict__.items() if k not in excluded_keys
        }
        extra_fields["service_name"] = "app_api"
        if "logger" in extra_fields:
            del log_record["logger"]

        log_record["extra_fields"] = sanitize_for_json(extra_fields)

        return json.dumps(log_record, ensure_ascii=False, default=str)


log_config_gcp = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": JsonFormatter
        }
    },
    "handlers": {
        "default": {
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "handlers": ["default"],
        "level": "INFO",
    },
}

log_config_local = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "rich": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%d-%m-%Y %H:%M:%S"
        }
    },
    "handlers": {
        "default": {
            "class": "rich.logging.RichHandler",
            "formatter": "rich",
            "rich_tracebacks": True,
            "tracebacks_show_locals": True,
            "show_time": True,
            "show_level": True,
            "show_path": True,
            "markup": True
        }
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "DEBUG", "propagate": True},
        "uvicorn.error": {
            "handlers": ["default"], "level": "DEBUG", "propagate": True
        },
        "uvicorn.access": {
            "handlers": ["default"], "level": "DEBUG", "propagate": False
        }
    }
}

if ENV_MODE == "dev":
    log_config_gcp["root"]["level"] = "DEBUG"

if __name__ == "__main__":

    kwargs = {
        "app": FASTAPI_APP,
        "host": HOST,
        "port": int(PORT),
        "reload": False,
        "workers": multiprocessing.cpu_count() * 2 + 1,
        "log_config": log_config_local if ENV_MODE == "local" else log_config_gcp,
        "proxy_headers": True,
    }
    if ENV_MODE == "prod":
        uvicorn.run(**kwargs)
    else:
        del kwargs["workers"]  # Workers are not supported in reload mode
        kwargs["reload"] = True
        kwargs["log_level"] = "debug"
        uvicorn.run(**kwargs)
