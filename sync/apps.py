# sync/apps.py
import os, threading
from django.apps import AppConfig

class SyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sync"

    def ready(self):
        if os.environ.get("RUN_SYNC_WORKER") != "1":
            return
        import sys
        from django.conf import settings
        if settings.ROLE != "terminal":
            return
        # autoreloader sets RUN_MAIN in its child; --noreload never does — accept both
        if os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv:
            from .engine import worker
            threading.Thread(target=worker, daemon=True).start()