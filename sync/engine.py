import time

import requests
from django.db import close_old_connections
from django.utils import timezone

from . import config, payloads
from .models import OutboxRecord, get_state, set_state

SESSION = requests.Session()


def headers():
    cfg = config.device_config()
    return {"X-Device-ID": cfg["device_id"], "X-Device-Key": cfg["device_key"]}


def ping(timeout=3):
    cfg = config.device_config()
    if not cfg:
        return False
    try:
        r = SESSION.head(
            f"{cfg['central_url']}/api/sync/ping/", timeout=timeout, headers=headers()
        )
        return r.status_code == 200
    except requests.RequestException:
        return False


def push(batch=100):
    cfg = config.device_config()
    pending = list(
        OutboxRecord.objects.filter(pushed_at__isnull=True).order_by("id")[:batch]
    )
    if not (cfg and pending):
        return 0
    r = SESSION.post(
        f"{cfg['central_url']}/api/sync/upload/",
        json={
            "events": [
                {"event_id": str(p.event_id), "entity": p.entity, "payload": p.payload}
                for p in pending
            ]
        },
        headers=headers(),
        timeout=30,
    )
    r.raise_for_status()
    ok = {p.id for p in pending if str(p.event_id) in set(r.json()["accepted"])}
    return OutboxRecord.objects.filter(id__in=ok).update(pushed_at=timezone.now())


def pull():
    cfg = config.device_config()
    r = SESSION.get(
        f"{cfg['central_url']}/api/sync/download/",
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
    if not config.is_paired():
        return {"online": False, "error": "not paired yet"}
    result = {"online": ping()}
    if result["online"]:
        try:
            result["pushed"] = push()  # PUSH FIRST — central's stock numbers
            result["pulled"] = pull()  # must include this till's deltas
            set_state("last_sync_at", timezone.now().isoformat())
        except requests.RequestException as e:
            result["error"] = str(e)
    set_state("last_ping_ok", str(result["online"]).lower())
    return result


def worker(interval=30):
    while True:
        try:
            run_sync()
        except Exception:
            pass
        finally:
            close_old_connections()
        time.sleep(interval)
