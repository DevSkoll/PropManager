from django.urls import path

from . import views

app_name = "accounts_tenant"

urlpatterns = [
    path("login/", views.tenant_login, name="tenant_login"),
]
