from django.http import HttpResponse


def health(_request):
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")
