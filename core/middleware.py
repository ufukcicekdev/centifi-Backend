from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Railway / iç probe bazen Host: 127.0.0.1 ile gelir; CommonMiddleware öncesi
    200 dönersek DisallowedHost ve ağır middleware zinciri devreye girmez.
    """

    def process_request(self, request):
        if request.path in ("/health", "/health/"):
            return HttpResponse("ok", content_type="text/plain; charset=utf-8")
        return None
