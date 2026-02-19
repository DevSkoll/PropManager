from django.urls import path

from . import views

app_name = "rewards_admin"

urlpatterns = [
    path(
        "rewards/properties/",
        views.admin_property_rewards_list,
        name="property_rewards_list",
    ),
    path(
        "rewards/properties/<uuid:property_pk>/config/",
        views.admin_property_rewards_config,
        name="property_rewards_config",
    ),
    path("rewards/grant/", views.admin_grant_reward, name="grant_reward"),
    path(
        "rewards/tenants/<uuid:tenant_pk>/adjust/",
        views.admin_adjust_balance,
        name="adjust_balance",
    ),
    path("rewards/balances/", views.admin_reward_balances, name="reward_balances"),
    path("rewards/history/", views.admin_reward_history, name="reward_history"),
    path(
        "rewards/tenants/<uuid:tenant_pk>/",
        views.admin_tenant_reward_detail,
        name="tenant_reward_detail",
    ),
]
