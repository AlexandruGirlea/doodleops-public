"""
All API URL's will follow the pattern:
/features/<api_app_url_path>/<api_url_path>/
"""

from django.urls import path

from app_api import views

urlpatterns = [
    path(
        "features/<str:api_app_url_path>/<path:api_url_path>",
        views.generic_api_view,
        name="generic_api_view",
    ),
]
