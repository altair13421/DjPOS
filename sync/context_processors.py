# sync/context_processors.py
from .models import OutboxRecord, get_state
import os

def sync_status(request):
    return {
        "sync_online": get_state("last_ping_ok") == "true",
        "sync_pending": OutboxRecord.objects.filter(pushed_at__isnull=True).count(),
        "app_role": os.environ.get("APP_ROLE", "server"),
    }
