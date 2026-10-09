from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from users.models import Organization
from .auth import TerminalKeyAuth
from .models import Terminal


class TerminalKeyAuthTests(TestCase):
    def test_authenticated_terminal_is_available_on_request(self):
        organization = Organization.objects.create(name="Test", slug="test")
        terminal = Terminal.objects.create(
            organization=organization,
            name="Front counter",
            device_id="terminal-1",
            api_key="test-key",
        )
        request = Request(
            APIRequestFactory().get(
                "/",
                HTTP_X_DEVICE_ID=terminal.device_id,
                HTTP_X_DEVICE_KEY=terminal.api_key,
            )
        )

        authenticated_terminal, auth = TerminalKeyAuth().authenticate(request)

        self.assertIs(authenticated_terminal, terminal)
        self.assertIsNone(auth)
        self.assertIs(request.terminal, terminal)
