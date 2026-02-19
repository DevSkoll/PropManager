from django.urls import path

from . import views

app_name = "communications_admin"

urlpatterns = [
    path("communications/", views.admin_thread_list, name="thread_list"),
    path("communications/create/", views.admin_thread_create, name="thread_create"),
    path("communications/<uuid:pk>/", views.admin_thread_detail, name="thread_detail"),
    path("announcements/", views.admin_announcement_list, name="announcement_list"),
    path("announcements/create/", views.admin_announcement_create, name="announcement_create"),
    path("announcements/<uuid:pk>/edit/", views.admin_announcement_edit, name="announcement_edit"),
]
