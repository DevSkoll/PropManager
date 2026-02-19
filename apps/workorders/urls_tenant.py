from django.urls import path

from . import views

app_name = "workorders_tenant"

urlpatterns = [
    path("workorders/", views.tenant_workorder_list, name="workorder_list"),
    path("workorders/create/", views.tenant_workorder_create, name="workorder_create"),
    path("workorders/<uuid:pk>/", views.tenant_workorder_detail, name="workorder_detail"),
    path("workorders/<uuid:pk>/note/", views.tenant_workorder_add_note, name="workorder_add_note"),
]
