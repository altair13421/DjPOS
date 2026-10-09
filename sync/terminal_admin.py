# sync/terminal_admin.py
import secrets
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import PairingCode, Terminal


@login_required
def terminals(request):
    org = (
        request.user.memberships.first().organization
    )  # ⚠ use however YOUR views resolve the active org
    if request.method == "POST":
        code = secrets.token_hex(4).upper()  # 8 chars, e.g. "3FA9C21B"
        PairingCode.objects.create(
            organization=org,
            code=code,
            terminal_name=request.POST.get("name") or "Till",
            expires_at=timezone.now() + timedelta(minutes=10),
            created_by=request.user,
        )
        return redirect("terminals")
    
    return render(
        request,
        "sync/terminals.html",
        {
            "codes": PairingCode.objects.filter(
                organization=org, used=False, expires_at__gt=timezone.now()
            ),
            "unused_codes": PairingCode.objects.filter(
                organization=org, used=False,
            ).order_by("-created_at")[:10],
            "terminals": Terminal.objects.filter(organization=org),
        },
    )
