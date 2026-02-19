from django.urls import path

from . import views

app_name = "communications_admin"

urlpatterns = [
    path("communications/", views.thread_list, name="thread_list"),
]
