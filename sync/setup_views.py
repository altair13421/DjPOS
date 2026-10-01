# sync/setup_views.py  (till only)
from django.http import JsonResponse
import requests as rq
from django.shortcuts import render, redirect
from django.conf import settings
from . import config
from .engine import run_sync


def ping(request):
    if config.is_paired():
        return redirect("/")
    error = None
    try:
        device_cfg = config.device_config()
        r = rq.head(f"{device_cfg['central_url']}/api/sync/ping/", timeout=10)
        if r.status_code == 200:
            return JsonResponse({"status": "ok", "server_time": r.headers.get("Date")})
        return JsonResponse({"status": "Could not reach the central server.", "server_time": r.headers.get("Date")}, status=r.status_code)
    except rq.RequestException:
        return JsonResponse({"status": "Could not reach the central server.", "server_time": r.headers.get("Date")}, status=503)


def setup(request):
    if config.is_paired():
        return redirect("/")
    error = None
    if request.method == "POST":
        central = request.POST.get("central_url", "").strip().rstrip("/")
        if "://" not in central:
            central = "http://" + central
        code = request.POST.get("code", "").strip().upper()
        try:
            r = rq.post(f"{central}/api/sync/pair/", json={"code": code}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                config.save_device_config(
                    {
                        "central_url": central,
                        "device_id": data["device_id"],
                        "device_key": data["device_key"],
                        "organization": data["organization"],
                    }
                )
                run_sync()  # first pull happens right now
                return redirect("/users/login/")  # ⚠ your login URL
            error = r.json().get("error", "Central rejected the code.")
        except rq.RequestException:
            error = "Could not reach the central server — check the URL and internet."
    return render(request, "sync/setup.html", {"error": error})
