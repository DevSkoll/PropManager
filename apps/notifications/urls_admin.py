from django.urls import path

from . import views

app_name = "notifications_admin"

urlpatterns = [
    # Groups
    path("notifications/groups/", views.admin_group_list, name="group_list"),
    path("notifications/groups/create/", views.admin_group_create, name="group_create"),
    path("notifications/groups/<uuid:pk>/", views.admin_group_detail, name="group_detail"),
    path("notifications/groups/<uuid:pk>/edit/", views.admin_group_edit, name="group_edit"),
    path("notifications/groups/<uuid:pk>/delete/", views.admin_group_delete, name="group_delete"),
    # Contacts
    path("notifications/groups/<uuid:group_pk>/contacts/add/", views.admin_contact_add, name="contact_add"),
    path("notifications/contacts/<uuid:pk>/edit/", views.admin_contact_edit, name="contact_edit"),
    path("notifications/contacts/<uuid:pk>/delete/", views.admin_contact_delete, name="contact_delete"),
    # Reminders
    path("notifications/invoices/<uuid:invoice_pk>/remind/", views.admin_send_reminder, name="send_reminder"),
]
