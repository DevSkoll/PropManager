from django.shortcuts import render


def workorder_list(request):
    return render(request, "workorders/workorder_list.html")
