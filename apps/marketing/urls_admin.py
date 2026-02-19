from django.urls import path

from . import views

app_name = "marketing_admin"

urlpatterns = [
    path("marketing/campaigns/", views.campaign_list, name="campaign_list"),
]
