"""
Public onboarding URLs for tenant self-service flow.
"""

from django.urls import path

from . import views_onboarding

urlpatterns = [
    # Entry point and routing
    path("start/<str:token>/", views_onboarding.onboarding_start, name="onboarding_start"),
    path("session/<str:token>/", views_onboarding.onboarding_router, name="onboarding_router"),

    # Account creation steps
    path("session/<str:token>/verify/", views_onboarding.onboarding_verify, name="onboarding_verify"),
    path("session/<str:token>/otp/", views_onboarding.onboarding_otp, name="onboarding_otp"),
    path("session/<str:token>/create-account/", views_onboarding.onboarding_create_account, name="onboarding_account_creation"),

    # Information collection steps
    path("session/<str:token>/personal-info/", views_onboarding.onboarding_personal_info, name="onboarding_personal_info"),

    path("session/<str:token>/emergency-contacts/", views_onboarding.onboarding_emergency_contacts, name="onboarding_emergency_contacts"),
    path("session/<str:token>/emergency-contacts/complete/", views_onboarding.onboarding_emergency_contacts_complete, name="onboarding_emergency_contacts_complete"),

    path("session/<str:token>/occupants/", views_onboarding.onboarding_occupants, name="onboarding_occupants"),
    path("session/<str:token>/occupants/complete/", views_onboarding.onboarding_occupants_complete, name="onboarding_occupants_complete"),

    path("session/<str:token>/pets/", views_onboarding.onboarding_pets, name="onboarding_pets"),
    path("session/<str:token>/pets/complete/", views_onboarding.onboarding_pets_complete, name="onboarding_pets_complete"),

    path("session/<str:token>/vehicles/", views_onboarding.onboarding_vehicles, name="onboarding_vehicles"),
    path("session/<str:token>/vehicles/complete/", views_onboarding.onboarding_vehicles_complete, name="onboarding_vehicles_complete"),

    path("session/<str:token>/employment/", views_onboarding.onboarding_employment, name="onboarding_employment"),

    path("session/<str:token>/insurance/", views_onboarding.onboarding_insurance, name="onboarding_insurance"),

    path("session/<str:token>/id-verification/", views_onboarding.onboarding_id_verification, name="onboarding_id_verification"),

    # Document signing
    path("session/<str:token>/documents/", views_onboarding.onboarding_documents, name="onboarding_documents"),
    path("session/<str:token>/documents/complete/", views_onboarding.onboarding_documents_complete, name="onboarding_documents_complete"),
    path("session/<str:token>/documents/<int:doc_pk>/sign/", views_onboarding.onboarding_sign_document, name="onboarding_sign_document"),

    # Fee review (acknowledgment only, no payment during onboarding)
    path("session/<str:token>/payments/", views_onboarding.onboarding_payments, name="onboarding_payments"),
    path("session/<str:token>/payments/complete/", views_onboarding.onboarding_payments_complete, name="onboarding_payments_complete"),

    # Final steps
    path("session/<str:token>/move-in-schedule/", views_onboarding.onboarding_move_in_schedule, name="onboarding_move_in_schedule"),
    path("session/<str:token>/welcome/", views_onboarding.onboarding_welcome, name="onboarding_welcome"),
    path("session/<str:token>/welcome/complete/", views_onboarding.onboarding_welcome_complete, name="onboarding_welcome_complete"),
    path("session/<str:token>/complete/", views_onboarding.onboarding_complete, name="onboarding_complete"),

    # AJAX endpoints for dynamic forms
    path("session/<str:token>/api/contact/<int:pk>/delete/", views_onboarding.api_delete_contact, name="api_delete_contact"),
    path("session/<str:token>/api/occupant/<int:pk>/delete/", views_onboarding.api_delete_occupant, name="api_delete_occupant"),
    path("session/<str:token>/api/pet/<int:pk>/delete/", views_onboarding.api_delete_pet, name="api_delete_pet"),
    path("session/<str:token>/api/vehicle/<int:pk>/delete/", views_onboarding.api_delete_vehicle, name="api_delete_vehicle"),
]
