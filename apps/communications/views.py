from django.shortcuts import render


def thread_list(request):
    return render(request, "communications/thread_list.html")
