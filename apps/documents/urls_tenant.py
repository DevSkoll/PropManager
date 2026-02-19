from django.urls import path

from . import views

app_name = "documents_tenant"

urlpatterns = [
    path("documents/", views.tenant_document_list, name="document_list"),
    path("documents/upload/", views.tenant_document_upload, name="document_upload"),
    path("documents/<uuid:pk>/", views.tenant_document_detail, name="document_detail"),
    path("documents/<uuid:pk>/delete/", views.tenant_document_delete, name="document_delete"),
    path("documents/<uuid:pk>/download/", views.tenant_document_download, name="document_download"),
    path("documents/<uuid:pk>/preview/", views.tenant_document_preview, name="document_preview"),
    path("documents/folders/create/", views.tenant_folder_create, name="folder_create"),
]
