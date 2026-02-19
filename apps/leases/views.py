from django.shortcuts import render


def lease_list(request):
    return render(request, "leases/lease_list.html")
