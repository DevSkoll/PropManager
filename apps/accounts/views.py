from django.shortcuts import render


def tenant_login(request):
    return render(request, "tenant/login.html")


def admin_login(request):
    return render(request, "admin_portal/login.html")
