from django.urls import path
from django.conf import settings

from app_pages import views

urlpatterns = [
    path("", views.index, name="index"),
    path("services/", views.services, name="services"),
    path('search/', views.search_apis, name='search_apis'),
    path("services/filter/<str:api_app_url_path>/", views.services, name="services"),
    path("suggest-new-feature/", views.suggest_new_feature, name="suggest_new_feature"),
    path("about/", views.about, name="about"),
    path("blog/", views.blog, name="blog"),
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("cookie-policy/", views.cookie_policy, name="cookie_policy"),
]


if settings.DEBUG:  # display custom error pages only in DEBUG mode
    urlpatterns += [
        path('400/', views.custom_400_view),
        path('403/', views.custom_403_view),
        path('404/', views.custom_404_view),
        path('500/', views.custom_500_view),
    ]
