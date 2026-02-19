from django.urls import path

from . import views

app_name = "rewards_tenant"

urlpatterns = [
    path("rewards/", views.tenant_rewards_dashboard, name="rewards_dashboard"),
    path(
        "rewards/apply/<uuid:invoice_pk>/",
        views.tenant_apply_rewards,
        name="apply_rewards",
    ),
    path("rewards/history/", views.tenant_reward_history, name="reward_history"),
]
