# sync/management/commands/register_terminal.py  — run ON THE CENTRAL SERVER
import secrets
from django.core.management.base import BaseCommand
from sync.models import Terminal
from users.models import Organization

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--org", type=int, required=True)
        parser.add_argument("--name", default="Till")

    def handle(self, *args, **opts):
        t = Terminal.objects.create(
            organization=Organization.objects.get(pk=opts["org"]), name=opts["name"],
            device_id=f"TILL-{secrets.token_hex(3).upper()}")
        self.stdout.write(self.style.SUCCESS(
            f"Put these in the till's environment:\n  DEVICE_ID={t.device_id}\n  DEVICE_KEY={t.api_key}"))