from django.shortcuts import redirect
from . import config

EXEMPT = ("/setup/", "/static/")


class TerminalSetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not config.is_paired() and not request.path.startswith(EXEMPT):
            return redirect("/setup/")
        if config.is_paired() and request.path == "/setup/":
            return redirect("/")
        return self.get_response(request)
