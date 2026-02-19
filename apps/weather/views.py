from django.shortcuts import render


def weather_dashboard(request):
    return render(request, "weather/dashboard.html")
