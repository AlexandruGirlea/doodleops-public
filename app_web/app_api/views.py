import logging
from urllib.parse import urljoin

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404


from app_api.models import API
from common.auth import encrypt_str

logger = logging.getLogger(__name__)


def generic_api_view(request, api_app_url_path: str, api_url_path: str):
    if request.method != "GET":
        return HttpResponse("Only GET method is allowed", status=405)

    api = get_object_or_404(
        API, url_path=api_url_path, api_app__url_path=api_app_url_path
    )

    context = {
        "api": api,
        "FASTAPI_HOST": settings.FASTAPI_HOST
    }

    user_obj = None
    if request.user.is_authenticated:
        user_obj = request.user

    if not user_obj and not api.active:  # hide public view of inactive APIs
        raise Http404
    elif not user_obj and api.active:  # public view of active APIs
        return render(request, f"{api.html_template_path}", context)
    elif user_obj and not user_obj.is_staff and not api.active:
        logger.warning(
            f"User {user_obj.username} tried to access inactive API "
            f"{api.url_path}."
        )
        raise Http404  # hide inactive APIs from non-staff users
    elif user_obj and (user_obj.is_staff or api.active):
        context["fast_api_path_full_path"] = urljoin(
            settings.FASTAPI_HOST, api.url_path.lstrip("/")
        )
        context["token"] = encrypt_str(
            f"{request.session.session_key}:{request.user.username}"
        )

    return render(request, f"{api.html_template_path}", context)
