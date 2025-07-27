from urllib.parse import urljoin

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from app_api.models import CostOfLLMAppAI

register = template.Library()


@register.simple_tag
def get_svg_path(svg_name):
    return urljoin(settings.STATIC_URL, f"assets/svg/logos/{svg_name}")


@register.simple_tag
def get_app_api_doc_url():
    return urljoin(settings.FASTAPI_HOST, "doc")


@register.simple_tag
def google_tag():
    if settings.ENV_MODE == 'dev':
        # replace with actual Google Tag Manager code for development
        return mark_safe("")
    elif settings.ENV_MODE == 'prod':
        # replace with actual Google Tag Manager code for production
        return mark_safe("")
    else:
        return ""


@register.simple_tag
def hotjar_tag():
    if settings.ENV_MODE in {'dev', 'prod'}:
        # replace with actual Hotjar code for both development and production
        return mark_safe("")
    else:
        return ""


@register.simple_tag
def get_llm_cost():
    return CostOfLLMAppAI.objects.all()
