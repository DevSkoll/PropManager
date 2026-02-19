from django.urls import path

from . import views

app_name = "marketing_admin"

urlpatterns = [
    # Campaign CRUD
    path("marketing/campaigns/", views.campaign_list, name="campaign_list"),
    path("marketing/campaigns/create/", views.campaign_create, name="campaign_create"),
    path("marketing/campaigns/<uuid:pk>/", views.campaign_detail, name="campaign_detail"),
    path("marketing/campaigns/<uuid:pk>/edit/", views.campaign_edit, name="campaign_edit"),
    path("marketing/campaigns/<uuid:pk>/preview/", views.campaign_preview, name="campaign_preview"),
    path("marketing/campaigns/<uuid:pk>/send/", views.campaign_send, name="campaign_send"),
    path("marketing/campaigns/<uuid:pk>/cancel/", views.campaign_cancel, name="campaign_cancel"),
    # Tracking (no auth - called from emails)
    path("marketing/track/open/<uuid:recipient_pk>/", views.tracking_pixel, name="tracking_pixel"),
    path("marketing/track/click/<str:tracking_token>/", views.tracking_redirect, name="tracking_redirect"),
]
