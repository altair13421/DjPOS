import time

import requests
from django.db import close_old_connections
from django.utils import timezone

from . import config, payloads
from .models import OutboxRecord, get_state, set_state
from users.models import Organization

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
    organization = payloads.apply_catalog(data)
    set_state("organization_id", str(organization.pk))
    set_state("catalog_version", str(data["catalog_version"]))
    return len(data["items"])


def pull_sales_history():
    cfg = config.device_config()
    if get_state("sales_history_complete", "false") == "true":
        return 0

    cursor = int(get_state("sales_history_cursor", "0"))
    imported = 0
    while True:
        r = SESSION.get(
            f"{cfg['central_url']}/api/sync/sales-history/",
            params={"after": cursor},
            headers=headers(),
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        sales = data.get("sales")
        next_cursor = data.get("next_cursor")
        complete = data.get("complete")
        organization_id = data.get("organization_id")
        if (
            not isinstance(sales, list)
            or not isinstance(next_cursor, int)
            or not isinstance(complete, bool)
            or not isinstance(organization_id, int)
        ):
            raise ValueError("Invalid server sales history response")
        stored_org_id = get_state("organization_id")
        if stored_org_id and stored_org_id != str(organization_id):
            raise ValueError("Sales history organization does not match this terminal")
        if sales and next_cursor <= cursor:
            raise ValueError("Server sales history cursor did not advance")
        if not sales and not complete:
            raise ValueError("Server sales history returned an empty incomplete page")

        if sales:
            organization = Organization.objects.get(pk=organization_id)
            imported += payloads.apply_sales_history(sales, organization)
            cursor = next_cursor
            set_state("sales_history_cursor", str(cursor))
            set_state("organization_id", str(organization_id))
        if complete:
            set_state("sales_history_complete", "true")
            return imported

def run_sync():
    if not config.is_paired():
        return {"online": False, "error": "not paired yet"}
    result = {"online": ping()}
    if result["online"]:
        try:
            result["pushed"] = push()  # PUSH FIRST — central's stock numbers
            result["pulled"] = pull()  # must include this till's deltas
            result["sales_imported"] = pull_sales_history()
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
