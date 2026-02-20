from django.urls import path

from . import views
from . import views_tenant_edocs as edoc_views

app_name = "documents_tenant"

urlpatterns = [
    # Regular Documents
    path("documents/", views.tenant_document_list, name="document_list"),
    path("documents/upload/", views.tenant_document_upload, name="document_upload"),
    path("documents/<uuid:pk>/", views.tenant_document_detail, name="document_detail"),
    path("documents/<uuid:pk>/delete/", views.tenant_document_delete, name="document_delete"),
    path("documents/<uuid:pk>/download/", views.tenant_document_download, name="document_download"),
    path("documents/<uuid:pk>/preview/", views.tenant_document_preview, name="document_preview"),
    path("documents/folders/create/", views.tenant_folder_create, name="folder_create"),

    # eDocuments (Electronic Signing)
    path("documents/edocs/", edoc_views.tenant_edoc_list, name="edoc_list"),
    path("documents/edocs/<uuid:pk>/", edoc_views.tenant_edoc_detail, name="edoc_detail"),
    path("documents/edocs/<uuid:pk>/sign/", edoc_views.tenant_edoc_sign, name="edoc_sign"),
    path("documents/edocs/<uuid:pk>/pdf/", edoc_views.tenant_edoc_download_pdf, name="edoc_pdf"),
]
