import time

import requests
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from . import payloads
from .models import OutboxRecord, get_state, set_state

SESSION = requests.Session()  # reuses connections


def headers():
    return {"X-Device-ID": settings.DEVICE_ID, "X-Device-Key": settings.DEVICE_KEY}


def ping(timeout=3):
    try:
        r = SESSION.head(
            f"{settings.CENTRAL_URL}/api/sync/ping/", timeout=timeout, headers=headers()
        )
        return r.status_code == 200
    except requests.RequestException:  # DNS fail / timeout / refused = offline
        return False


def push(batch=100):
    pending = list(
        OutboxRecord.objects.filter(pushed_at__isnull=True).order_by("id")[:batch]
    )
    if not pending:
        return 0
    r = SESSION.post(
        f"{settings.CENTRAL_URL}/api/sync/upload/",
        json={
            "events": [
                {"event_id": str(p.event_id), "entity": p.entity, "payload": p.payload}
                for p in pending
            ]
        },
        headers=headers(),
        timeout=30,
    )
    r.raise_for_status()  # no ack → nothing marked → whole batch retried later
    ok = {p.id for p in pending if str(p.event_id) in set(r.json()["accepted"])}
    return OutboxRecord.objects.filter(id__in=ok).update(pushed_at=timezone.now())


def pull():
    r = SESSION.get(
        f"{settings.CENTRAL_URL}/api/sync/download/",
        params={"catalog_version": get_state("catalog_version", "-1")},
        headers=headers(),
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("update"):
        return 0
    payloads.apply_catalog(data)
    set_state("catalog_version", str(data["catalog_version"]))
    return len(data["items"])


def run_sync():
    result = {"online": ping()}
    if result["online"]:
        try:
            result["pushed"] = push()  # PUSH FIRST — central's stock snapshot must
            result["pulled"] = pull()  # already include this till's deltas
            set_state("last_sync_at", timezone.now().isoformat())
        except requests.RequestException as e:
            result["error"] = str(e)  # everything stays queued, retried next cycle
    set_state("last_ping_ok", str(result["online"]).lower())
    return result


def worker(interval=30):
    while True:
        try:
            run_sync()
        except Exception:
            pass  # never let the worker die
        finally:
            close_old_connections()  # required in long-running threads
        time.sleep(interval)
