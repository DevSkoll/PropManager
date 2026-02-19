from django.urls import path

from . import views

app_name = "workorders_admin"

urlpatterns = [
    path("workorders/", views.workorder_list, name="workorder_list"),
]
