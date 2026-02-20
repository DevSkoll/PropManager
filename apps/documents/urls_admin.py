from django.urls import path

from . import views
from . import views_edocuments as edoc_views

app_name = "documents_admin"

urlpatterns = [
    # Regular Documents
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

    # eDocument Templates
    path("edocs/templates/", edoc_views.admin_template_list, name="template_list"),
    path("edocs/templates/create/", edoc_views.admin_template_create, name="template_create"),
    path("edocs/templates/<uuid:pk>/", edoc_views.admin_template_detail, name="template_detail"),
    path("edocs/templates/<uuid:pk>/edit/", edoc_views.admin_template_edit, name="template_edit"),
    path("edocs/templates/<uuid:pk>/delete/", edoc_views.admin_template_delete, name="template_delete"),
    path("edocs/templates/<uuid:pk>/preview/", edoc_views.admin_template_preview, name="template_preview"),

    # eDocuments
    path("edocs/", edoc_views.admin_edoc_list, name="edoc_list"),
    path("edocs/create/", edoc_views.admin_edoc_create, name="edoc_create"),
    path("edocs/<uuid:pk>/", edoc_views.admin_edoc_detail, name="edoc_detail"),
    path("edocs/<uuid:pk>/edit/", edoc_views.admin_edoc_edit, name="edoc_edit"),
    path("edocs/<uuid:pk>/signers/", edoc_views.admin_edoc_assign_signers, name="edoc_assign_signers"),
    path("edocs/<uuid:pk>/send/", edoc_views.admin_edoc_send, name="edoc_send"),
    path("edocs/<uuid:pk>/cancel/", edoc_views.admin_edoc_cancel, name="edoc_cancel"),
    path("edocs/<uuid:pk>/pdf/", edoc_views.admin_edoc_pdf, name="edoc_pdf"),
    path("edocs/<uuid:pk>/sign/", edoc_views.admin_edoc_sign_as_landlord, name="edoc_sign_landlord"),
]
