# sync/setup_views.py  (till only)
from django.http import JsonResponse
from django.views.generic.edit import FormView
import requests as rq
from django.shortcuts import redirect

from .forms import SetupForm
from . import config
from .engine import run_sync


def ping(request):
    try:
        device_cfg = config.device_config()
        r = rq.head(f"{device_cfg['central_url']}/api/sync/ping/", timeout=10)
        if r.status_code == 200:
            return JsonResponse({"status": "ok", "server_time": r.headers.get("Date")})
        return JsonResponse(
            {
                "status": "Could not reach the central server.",
                "server_time": r.headers.get("Date"),
            },
            status=r.status_code,
        )
    except rq.RequestException:
        return JsonResponse(
            {
                "status": "Could not reach the central server.",
                "server_time": r.headers.get("Date"),
            },
            status=503,
        )


class SetupView(FormView):
    template_name = "sync/setup.html"
    form_class = SetupForm
    success_url = "/users/login/"

    def dispatch(self, request, *args, **kwargs):
        if config.is_paired():
            return redirect("/")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        central = form.cleaned_data["central_url"].strip().rstrip("/")
        if "://" not in central:
            central = "http://" + central

        code = form.cleaned_data["code"].strip().upper()
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
                run_sync()
                return redirect(self.get_success_url())
            error = r.json().get("error", "Central rejected the code.")
        except rq.RequestException:
            error = "Could not reach the central server — check the URL and internet."

        return self.render_to_response(self.get_context_data(form=form, error=error))

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, error="Please correct the errors below.")
        )


setup = SetupView.as_view()
