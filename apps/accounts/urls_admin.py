from django.urls import path

from . import views

app_name = "accounts_admin"

urlpatterns = [
    path("login/", views.admin_login, name="admin_login"),
]
