from django.urls import path

from . import views

app_name = "documents_admin"

urlpatterns = [
    path("documents/", views.document_list, name="document_list"),
]
