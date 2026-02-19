from django.urls import path

from . import views

app_name = "workorders_admin"

urlpatterns = [
    path("workorders/", views.admin_workorder_list, name="workorder_list"),
    path("workorders/create/", views.admin_workorder_create, name="workorder_create"),
    path("workorders/<uuid:pk>/", views.admin_workorder_detail, name="workorder_detail"),
    path("workorders/<uuid:pk>/status/", views.admin_workorder_update_status, name="workorder_update_status"),
    path("workorders/<uuid:pk>/assign/", views.admin_workorder_assign, name="workorder_assign"),
]
