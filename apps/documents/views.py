from django.shortcuts import render


def document_list(request):
    return render(request, "documents/document_list.html")
