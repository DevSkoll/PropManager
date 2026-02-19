from django.urls import path

from . import views

app_name = "documents_admin"

urlpatterns = [
    path("documents/", views.admin_document_list, name="document_list"),
    path("documents/upload/", views.admin_document_upload, name="document_upload"),
    path("documents/<uuid:pk>/", views.admin_document_detail, name="document_detail"),
    path("documents/<uuid:pk>/delete/", views.admin_document_delete, name="document_delete"),
    path("documents/<uuid:pk>/download/", views.admin_document_download, name="document_download"),
]
