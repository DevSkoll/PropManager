from django.urls import path

from . import views

app_name = "documents_admin"

urlpatterns = [
    path("documents/", views.admin_document_list, name="document_list"),
    path("documents/upload/", views.admin_document_upload, name="document_upload"),
    path("documents/<uuid:pk>/", views.admin_document_detail, name="document_detail"),
    path("documents/<uuid:pk>/delete/", views.admin_document_delete, name="document_delete"),
    path("documents/<uuid:pk>/restore/", views.admin_document_restore, name="document_restore"),
    path("documents/<uuid:pk>/permanent-delete/", views.admin_document_permanent_delete, name="document_permanent_delete"),
    path("documents/<uuid:pk>/download/", views.admin_document_download, name="document_download"),
    path("documents/<uuid:pk>/preview/", views.admin_document_preview, name="document_preview"),
    path("documents/<uuid:pk>/lock/", views.admin_document_lock, name="document_lock"),
    path("documents/<uuid:pk>/unlock/", views.admin_document_unlock, name="document_unlock"),
    path("documents/folders/", views.admin_folder_list, name="folder_list"),
    path("documents/folders/create/", views.admin_folder_create, name="folder_create"),
    path("documents/folders/<uuid:pk>/", views.admin_folder_detail, name="folder_detail"),
]
