from django.urls import path

from . import views

app_name = "leases_signing"

urlpatterns = [
    # Public signing page (token-based, no login required)
    path("sign/<str:token>/", views.signing_page, name="signing_page"),
    path("sign/<str:token>/submit/", views.submit_signature, name="submit_signature"),
]
