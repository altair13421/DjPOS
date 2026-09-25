import hmac
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Terminal


class TerminalKeyAuth(BaseAuthentication):
    def authenticate(self, request):
        device_id = request.headers.get("X-Device-ID")
        key = request.headers.get("X-Device-Key")
        if not device_id or not key:
            return None
        terminal = Terminal.objects.filter(device_id=device_id, is_active=True).first()
        if not terminal or not hmac.compare_digest(terminal.api_key, key):
            raise AuthenticationFailed("Unknown device")
        return (terminal, None)   # → request.terminal