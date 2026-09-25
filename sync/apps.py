# sync/apps.py
import os, threading
from django.apps import AppConfig

class SyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sync"

    def ready(self):
        if os.environ.get("RUN_SYNC_WORKER") == "1" and os.environ.get("RUN_MAIN") == "true":
            from django.conf import settings
            if settings.ROLE == "terminal":
                from .engine import worker
                threading.Thread(target=worker, daemon=True).start()