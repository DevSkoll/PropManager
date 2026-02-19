from django.urls import path

from . import views

app_name = "documents_tenant"

urlpatterns = [
    path("documents/", views.tenant_document_list, name="document_list"),
    path("documents/<uuid:pk>/download/", views.tenant_document_download, name="document_download"),
]
