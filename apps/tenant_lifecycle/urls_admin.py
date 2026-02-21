"""
Admin URLs for tenant onboarding management.
"""

from django.urls import path

from . import views_admin

urlpatterns = [
    # Preset management
    path("presets/", views_admin.preset_list, name="admin_preset_list"),
    path("presets/<int:pk>/", views_admin.preset_detail, name="admin_preset_detail"),
    path("presets/<int:pk>/apply/", views_admin.preset_apply, name="admin_preset_apply"),

    # Template management
    path("templates/", views_admin.template_list, name="admin_template_list"),
    path("templates/create/", views_admin.template_create, name="admin_template_create"),
    path("templates/<int:pk>/", views_admin.template_detail, name="admin_template_detail"),
    path("templates/<int:pk>/edit/", views_admin.template_edit, name="admin_template_edit"),
    path("templates/<int:pk>/documents/", views_admin.template_documents, name="admin_template_documents"),
    path(
        "templates/<int:pk>/documents/<int:doc_pk>/delete/",
        views_admin.template_document_delete,
        name="admin_template_document_delete"
    ),
    path("templates/<int:pk>/fees/", views_admin.template_fees, name="admin_template_fees"),
    path(
        "templates/<int:pk>/fees/<int:fee_pk>/delete/",
        views_admin.template_fee_delete,
        name="admin_template_fee_delete"
    ),

    # Session management
    path("sessions/", views_admin.session_list, name="admin_session_list"),
    path("sessions/create/", views_admin.session_create, name="admin_session_create"),
    path("sessions/<int:pk>/", views_admin.session_detail, name="admin_session_detail"),
    path("sessions/<int:pk>/resend-invite/", views_admin.session_resend_invite, name="admin_session_resend_invite"),
    path("sessions/<int:pk>/regenerate-link/", views_admin.session_regenerate_link, name="admin_session_regenerate_link"),
    path("sessions/<int:pk>/cancel/", views_admin.session_cancel, name="admin_session_cancel"),
    path("sessions/<int:pk>/delete/", views_admin.session_delete, name="admin_session_delete"),
    path("sessions/<int:pk>/progress.json", views_admin.session_progress_json, name="admin_session_progress_json"),
]
