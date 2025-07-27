from django.urls import path

from app_contact.views import contact

urlpatterns = [
	path('contact/', contact, name='contact'),
]