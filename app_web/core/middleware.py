import logging

from django.http import HttpResponseNotFound
from django.conf import settings

logger = logging.getLogger(__name__)


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Replace the origin below with the one you want to allow
        response["Access-Control-Allow-Origin"] = "https://dev.doodleops.com"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
        return response


class Handle404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
                response.status_code == 404 and
                settings.ENV_MODE == "dev" and
                settings.DEBUG is True
        ):
            return HttpResponseNotFound('<h1>404 - Error - Page Not Found</h1>')
        return response
