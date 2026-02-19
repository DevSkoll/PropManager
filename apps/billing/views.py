from django.shortcuts import render


def invoice_list(request):
    return render(request, "billing/invoice_list.html")
