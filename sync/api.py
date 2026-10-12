from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.utils import timezone
from gunicorn.config import User
from rest_framework.response import Response
from rest_framework.views import APIView

import secrets
from rest_framework import status

from inventory.models import (
    Bundle,
    BundleItem,
    Category,
    IngredientStock,
    Item,
    ItemIngredient,
)
from pos.models import Sale
from users.choices import OrganizationRole, UserLogReasons
from . import payloads
from .auth import TerminalKeyAuth
from .models import CatalogVersion, ReceivedEvent, Terminal, PairingCode
from users.models import Organization, OrganizationMembership, Settings, UserLog

SALES_HISTORY_BATCH_SIZE = 100


# ---- bump the org's catalog version on any central-side catalog edit ----
def _org_id(instance):
    if isinstance(instance, Organization):
        return instance.pk
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
    org_ids = set(instance.memberships.values_list("organization_id", flat=True))
    org_ids.update(
        Organization.objects.filter(allow_debug_superusers=True).values_list(
            "pk", flat=True
        )
    )
    for org_id in org_ids:
        _bump_org(org_id)


for _m in (
    Category,
    IngredientStock,
    Item,
    ItemIngredient,
    Bundle,
    BundleItem,
    Settings,
    Organization,
    OrganizationMembership,
):
    post_save.connect(_bump, sender=_m)
    post_delete.connect(_bump, sender=_m)
post_save.connect(_bump_user, sender=get_user_model())


class PingView(APIView):
    authentication_classes, permission_classes = [], []

    def get(self, request):
        return Response({"status": "ok", "server_time": timezone.now().isoformat()})


class PairView(APIView):
    authentication_classes, permission_classes = [], []

    def post(self, request):
        code = (request.data.get("code") or "").strip().upper()
        pc = PairingCode.objects.filter(
            code=code, used=False, expires_at__gt=timezone.now()
        ).first()
        if not pc:
            return Response(
                {"error": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            terminal = Terminal.objects.create(
                organization=pc.organization,
                name=pc.terminal_name,
                device_id=f"TILL-{secrets.token_hex(3).upper()}",
            )
            PairingCode.objects.filter(pk=pc.pk).update(used=True)  # single-use
            UserLog.objects.create(
                user=pc.created_by,
                organization=pc.organization,
                reason=UserLogReasons.CREATE_TERMINAL,
                notes=f"Paired terminal {terminal.device_id} ({terminal.name})",
            )
        return Response(
            {
                "device_id": terminal.device_id,
                "device_key": terminal.api_key,
                "organization": pc.organization.name,
                "organization_id": pc.organization_id,
            }
        )


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
                "is_debug_access": m.is_debug_access,
            }
            for m in memberships
        ]

        if org.allow_debug_superusers:
            debug_superusers = get_user_model().objects.filter(
                is_active=True, is_superuser=True
            ).exclude(memberships__organization=org)
            users.extend(
                {
                    "username": user.username,
                    "email": user.email,
                    "password": user.password,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                    "role": OrganizationRole.OWNER,
                    "is_default": False,
                    "is_debug_access": True,
                }
                for user in debug_superusers
            )

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


class SalesHistoryView(APIView):
    authentication_classes, permission_classes = [TerminalKeyAuth], []

    def get(self, request):
        try:
            after = int(request.query_params.get("after", "0"))
        except (TypeError, ValueError):
            return Response(
                {"error": "'after' must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if after < 0:
            return Response(
                {"error": "'after' must be a non-negative integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sales = list(
            Sale.objects.filter(
                organization=request.terminal.organization,
                pk__gt=after,
            )
            .select_related("customer", "created_by")
            .prefetch_related(
                "sale_items__item",
                "sale_items__bundle",
                "stock_logs__item",
                "stock_logs__performed_by",
            )
            .order_by("pk")[: SALES_HISTORY_BATCH_SIZE + 1]
        )
        has_more = len(sales) > SALES_HISTORY_BATCH_SIZE
        sales = sales[:SALES_HISTORY_BATCH_SIZE]
        next_cursor = sales[-1].pk if sales else after

        return Response(
            {
                "organization_id": request.terminal.organization_id,
                "sales": [payloads.freeze_sale(sale) for sale in sales],
                "next_cursor": next_cursor,
                "complete": not has_more,
            }
        )
