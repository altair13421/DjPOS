from django.shortcuts import redirect
from . import config

EXEMPT = ("/setup/", "/static/")


class TerminalSetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not config.is_paired() and not request.path.startswith(EXEMPT):
            return redirect("sync:setup_terminal")
        if config.is_paired() and request.path == "/sync/setup/":
            return redirect("sync:terminal_list")
        return self.get_response(request)
