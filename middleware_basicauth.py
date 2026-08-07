"""Basic Auth OPCIONAL — ativa somente se BASIC_AUTH_PASS existir no .env.
Sem a variavel, o middleware e um no-op (site publico normal).
Permite manter o codigo identico entre ambientes (producao x teste).
"""
import base64
import os

from django.http import HttpResponse


class BasicAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        user = os.getenv("BASIC_AUTH_USER", "teste")
        password = os.getenv("BASIC_AUTH_PASS", "")
        self.enabled = bool(password)
        if self.enabled:
            self.expected = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        else:
            self.expected = ""

    def __call__(self, request):
        if self.enabled:
            auth = request.META.get("HTTP_AUTHORIZATION", "")
            if auth != self.expected:
                response = HttpResponse("Unauthorized", status=401)
                response["WWW-Authenticate"] = 'Basic realm="Statsfut Teste"'
                return response
        return self.get_response(request)
