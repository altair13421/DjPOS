from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import (
    Bundle,
    BundleItem,
    Category,
    IngredientStock,
    Item,
    ItemIngredient,
)
from . import payloads
from .auth import TerminalKeyAuth
from .models import CatalogVersion, ReceivedEvent, Terminal
from users.models import Organization, OrganizationMembership, Settings


# ---- bump the org's catalog version on any central-side catalog edit ----
def _org_id(instance):
    if getattr(instance, "organization_id", None):
        return instance.organization_id
    if getattr(instance, "item_id", None):
        return instance.item.organization_id  # ItemIngredient / BundleItem
    if getattr(instance, "ingredient_id", None):
        return instance.ingredient.organization_id
    return None


def _bump_org(org_id):
    with transaction.atomic():
        cv = CatalogVersion.objects.select_for_update().get_or_create(
            organization_id=org_id
        )[0]
        cv.value += 1
        cv.save()


def _bump(sender, instance, **kwargs):
    if settings.ROLE != "server":
        return
    org_id = _org_id(instance)
    if org_id:
        _bump_org(org_id)


def _bump_user(sender, instance, **kwargs):
    """User saves (password change, is_active=False) must reach every org they're in."""
    if settings.ROLE != "server":
        return
    for org_id in instance.memberships.values_list("organization_id", flat=True):
        _bump_org(org_id)


for _m in (
    Category,
    IngredientStock,
    Item,
    ItemIngredient,
    Bundle,
    BundleItem,
    Settings,
    OrganizationMembership,
):
    post_save.connect(_bump, sender=_m)
    post_delete.connect(_bump, sender=_m)
post_save.connect(_bump_user, sender=get_user_model())


class PingView(APIView):
    authentication_classes, permission_classes = [], []

    def get(self, request):
        return Response({"status": "ok", "server_time": timezone.now().isoformat()})


class UploadView(APIView):
    authentication_classes, permission_classes = [TerminalKeyAuth], []

    def post(self, request):
        org = (
            request.terminal.organization
        )  # org comes from the DEVICE, never the payload
        accepted, failed = [], []
        for ev in request.data.get("events", []):
            try:
                with transaction.atomic():
                    if ReceivedEvent.objects.filter(event_id=ev["event_id"]).exists():
                        result = "duplicate"
                    else:
                        result = payloads.THAWERS[ev["entity"]](ev["payload"], org)
                        ReceivedEvent.objects.create(
                            event_id=ev["event_id"],
                            terminal=request.terminal,
                            entity=ev["entity"],
                        )
                (accepted if result != "error" else failed).append(ev["event_id"])
            except Exception:
                failed.append(
                    ev["event_id"]
                )  # stays queued on the till — never silent loss
        Terminal.objects.filter(pk=request.terminal.pk).update(last_seen=timezone.now())
        return Response({"accepted": accepted, "failed": failed})


class DownloadView(APIView):
    authentication_classes, permission_classes = [TerminalKeyAuth], []

    def get(self, request):
        org = request.terminal.organization
        cv = CatalogVersion.objects.get_or_create(organization=org)[0]
        if request.query_params.get("catalog_version") == str(cv.value):
            return Response({"update": False, "catalog_version": cv.value})

        memberships = OrganizationMembership.objects.filter(
            organization=org, user__is_active=True
        ).select_related("user")
        users = [
            {
                "username": m.user.username,
                "email": m.user.email,
                "password": m.user.password,  # hash, never plaintext
                "first_name": m.user.first_name,
                "last_name": m.user.last_name,
                "is_active": m.user.is_active,
                "is_staff": m.user.is_staff,
                "is_superuser": m.user.is_superuser,
                "role": m.role,
                "is_default": m.is_default,
            }
            for m in memberships
        ]

        try:
            s = org.settings
            settings_payload = {
                "store_name": s.store_name,
                "store_address": s.store_address,
                "currency": s.currency,
                "owner_name": s.owner_name,
                "owner_phone_number": s.owner_phone_number,
                "store_category": s.store_category,
                "shift_duration": s.shift_duration,
            }
        except Settings.DoesNotExist:
            settings_payload = None

        return Response(
            {
                "update": True,
                "catalog_version": cv.value,
                "organization": {
                    "pk": org.pk,
                    "name": org.name,
                    "slug": org.slug,
                    "is_active": org.is_active,
                },
                "users": users,
                "settings": settings_payload,
                **payloads.catalog_snapshot(org),
            }
        )
