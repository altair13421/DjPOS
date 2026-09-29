# sync/setup_views.py  (till only)
import requests as rq
from django.shortcuts import render, redirect

from . import config
from .engine import run_sync


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
