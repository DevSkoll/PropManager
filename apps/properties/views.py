from django.shortcuts import render


def property_list(request):
    return render(request, "properties/property_list.html")
