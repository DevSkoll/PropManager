from django.urls import path

from . import views

app_name = "workorders_contractor"

urlpatterns = [
    path("<str:token>/", views.contractor_workorder_detail, name="workorder_detail"),
    path("<str:token>/update-status/", views.contractor_update_status, name="update_status"),
    path("<str:token>/notes/add/", views.contractor_add_note, name="add_note"),
    path("<str:token>/images/upload/", views.contractor_upload_image, name="upload_image"),
]
