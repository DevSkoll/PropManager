from django.urls import path

from . import views

app_name = "weather_admin"

urlpatterns = [
    path("weather/", views.weather_dashboard, name="weather_dashboard"),
]
