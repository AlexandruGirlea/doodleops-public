from django.urls import path

from app_users import views
from django.views.generic import RedirectView


urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("create-account/", views.create_account, name="create_account"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path(
        "profile/",
        RedirectView.as_view(pattern_name="profile_general"),
        name="profile-redirect",
    ),
    path(
        "profile/general/",
        views.profile_general,
        name="profile_general",
    ),
    path(
        "profile/personal-info/stripe-customer-portal/",
        views.redirect_to_stripe_customer_portal_url,
        name="stripe_customer_portal",
    ),
    path(
        "profile/personal-info/get-instant-cost-for-metered-subscription/",
        views.get_instant_cost_for_metered_subscription,
        name="get_instant_cost_for_metered_subscription",
    ),
    path("profile/security/", views.profile_security, name="profile_security"),
    path("profile/api-keys/", views.profile_api_keys, name="profile_api_keys"),
    path(
        "profile/delete_api_key/<uuid:token_id>/",
        views.profile_delete_api_keys,
        name="profile_delete_api_keys",
    ),
    path("profile/usage/", views.profile_api_usage, name="profile_api_usage"),
    path(
        "profile/personal-information/",
        views.profile_personal_information,
        name="profile_personal_information"
    ),
    path("delete-my-user/", views.delete_my_user, name="delete_my_user"),
    path('auth/google/login/', views.google_login, name='google_login'),
    path('auth/google/callback/', views.google_callback, name='google_callback'),
    path(
        'auth/validate-email/', views.validate_email_view, name='validate_email'
    ),
    path(
        'auth/password-reset/',
        views.password_reset,
        name='password_reset'
    ),
]
