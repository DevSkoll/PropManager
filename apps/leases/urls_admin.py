from django.urls import path

from . import views
from . import views_documents

app_name = "leases_admin"

urlpatterns = [
    path("leases/", views.admin_lease_list, name="lease_list"),
    path("leases/create/", views.admin_lease_create, name="lease_create"),
    path("leases/<uuid:pk>/", views.admin_lease_detail, name="lease_detail"),
    path("leases/<uuid:pk>/edit/", views.admin_lease_edit, name="lease_edit"),
    path("leases/<uuid:pk>/terms/add/", views.admin_lease_add_term, name="lease_add_term"),
    path("leases/<uuid:pk>/send-for-signature/", views.admin_send_for_signature, name="lease_send_signature"),
    path("leases/<uuid:pk>/mark-signed/", views.admin_mark_lease_signed, name="lease_mark_signed"),
    path("leases/<uuid:pk>/start-onboarding/", views.admin_lease_start_onboarding, name="lease_start_onboarding"),

    # Document linking and upload
    path("leases/<uuid:pk>/documents/available/", views_documents.lease_available_documents, name="lease_available_documents"),
    path("leases/<uuid:pk>/documents/link/", views_documents.lease_link_document, name="lease_link_document"),
    path("leases/<uuid:pk>/documents/unlink/", views_documents.lease_unlink_document, name="lease_unlink_document"),
    path("leases/<uuid:pk>/documents/link-multiple/", views_documents.lease_link_multiple_documents, name="lease_link_multiple"),
    path("leases/<uuid:pk>/documents/upload/", views_documents.lease_upload_document, name="lease_upload_document"),
]
