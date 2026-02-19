from django.shortcuts import render


def campaign_list(request):
    return render(request, "marketing/campaign_list.html")
