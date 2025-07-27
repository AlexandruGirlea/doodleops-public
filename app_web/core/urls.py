from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from oauth2_provider import urls as oauth2_urls

from app_financial.views import stripe_webhook
from app_pages.views import custom_admin_login_redirect


def set_path_env(name: str) -> str:
    """We use this because of CloudFlare Zero Trust for security."""
    if settings.ENV_MODE in ("local", "dev"):
        return settings.ENV_MODE + "/" + name
    return name


# used by oAuth to redirect to login if not authenticated
settings.LOGIN_URL = "/" + set_path_env("login/")

urlpatterns = [
    path(set_path_env("admin/login/"), custom_admin_login_redirect),
    path(set_path_env("admin/"), admin.site.urls),
    path(set_path_env(""), include("app_contact.urls")),
    path(set_path_env(""), include("app_pages.urls")),
    path(set_path_env(""), include("app_api.urls")),
    path(set_path_env(""), include("app_users.urls")),
    path(set_path_env("financial/"), include("app_financial.urls")),
    path("financial/stripe-webhook/", stripe_webhook, name="stripe_webhook"),
    path('o/', include(oauth2_urls)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# There is a middleware that handles 404 errors in development mode.
handler400 = 'app_pages.views.custom_400_view'
handler403 = 'app_pages.views.custom_403_view'
handler404 = 'app_pages.views.custom_404_view'
handler500 = 'app_pages.views.custom_500_view'
