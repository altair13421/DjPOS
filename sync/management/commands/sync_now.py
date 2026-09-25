# sync/management/commands/sync_now.py
import json
from django.core.management.base import BaseCommand
from sync.engine import run_sync
from sync.models import OutboxRecord

class Command(BaseCommand):
    def handle(self, *args, **opts):
        self.stdout.write(json.dumps(run_sync(), indent=2, default=str))
        pending = OutboxRecord.objects.filter(pushed_at__isnull=True).count()
        if pending:
            self.stdout.write(self.style.WARNING(f"⚠ {pending} records still queued"))