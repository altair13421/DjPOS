# sync/management/commands/sync_loop.py
from django.core.management.base import BaseCommand
from sync.engine import worker

class Command(BaseCommand):
    def handle(self, *args, **opts):
        worker()