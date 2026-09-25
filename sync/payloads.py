from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from users.models import Organization, OrganizationMembership, Settings, UserLog
from inventory.models import (
    Bundle,
    BundleItem,
    Category,
    IngredientStock,
    Item,
    ItemIngredient,
    StockLog,
)
from pos.models import CartItem, Customer, Sale
from .models import OutboxRecord


def enqueue(entity, payload):
    OutboxRecord.objects.create(entity=entity, payload=payload)


def _user(username):
    if not username:
        return None
    return (
        get_user_model().objects.filter(username=username).first()
    )  # ⚠ adjust if you log in by email


# ══════════════════ SALE BUNDLE (terminal → central) ══════════════════


def freeze_sale(sale):
    return {
        "uuid": str(sale.uuid),
        "device_id": sale.device_id or settings.DEVICE_ID,
        "sold_at": sale.created_at.isoformat(),
        "created_by": sale.created_by.username if sale.created_by else None,
        "customer": (
            None
            if sale.customer is None
            else {
                "uuid": str(sale.customer.uuid),
                "name": sale.customer.name,
                "email": sale.customer.email,
                "phone": sale.customer.phone,
                "address": sale.customer.address,
                "type_cus": sale.customer.type_cus,
            }
        ),
        "discount": str(sale.discount),
        "tax": str(sale.tax),
        "total": str(sale.total),
        "paid": str(sale.paid),
        "change": str(sale.change),
        "notes": sale.notes,
        "items": [
            {
                "uuid": str(ci.uuid),
                "item": str(ci.item.uuid) if ci.item_id else None,
                "bundle": str(ci.bundle.uuid) if ci.bundle_id else None,
                "quantity": ci.quantity,
                "unit_price": str(ci.unit_price),
                "stock_before": ci.stock_before,
                "stock_after": ci.stock_after,
                "notes": ci.notes,
            }
            for ci in sale.sale_items.select_related("item", "bundle")
        ],
        "stock_logs": [
            {
                "uuid": str(sl.uuid),
                "ingredient": str(sl.item.uuid),
                "performed_by": sl.performed_by.username if sl.performed_by else None,
                "change_quantity": sl.change_quantity,
                "reason": sl.reason,
                "revenue": str(sl.revenue),
                "cost": str(sl.cost),
                "note": sl.note,
                "created_at": sl.created_at.isoformat(),
            }
            for sl in sale.stock_logs.select_related("item")
        ],
    }


def enqueue_sale_bundle(sale):
    enqueue("sale", freeze_sale(sale))


def _thaw_customer(p, org):
    if p is None:
        return None
    return Customer.objects.get_or_create(
        uuid=p["uuid"],
        defaults={
            "organization": org,
            "name": p["name"],
            "email": p["email"],
            "phone": p["phone"],
            "address": p["address"],
            "type_cus": p["type_cus"],
        },
    )[0]


@transaction.atomic
def thaw_sale(p, org):
    if Sale.objects.filter(uuid=p["uuid"]).exists():
        return "duplicate"
    sale = Sale.objects.create(
        uuid=p["uuid"],
        device_id=p["device_id"],
        organization=org,
        created_by=_user(p["created_by"]),
        customer=_thaw_customer(p["customer"], org),
        discount=Decimal(p["discount"]),
        tax=Decimal(p["tax"]),
        total=Decimal(p["total"]),
        paid=Decimal(p["paid"]),
        change=Decimal(p["change"]),
        notes=p["notes"],
    )
    CartItem.objects.bulk_create(
        [
            CartItem(
                uuid=i["uuid"],
                sale=sale,
                item=Item.objects.get(uuid=i["item"]) if i["item"] else None,
                bundle=Bundle.objects.get(uuid=i["bundle"]) if i["bundle"] else None,
                quantity=i["quantity"],
                unit_price=Decimal(i["unit_price"]),
                stock_before=i["stock_before"],
                stock_after=i["stock_after"],
                notes=i["notes"],
            )
            for i in p["items"]
        ],
        ignore_conflicts=True,
    )
    for sl in p["stock_logs"]:
        StockLog.objects.create(
            uuid=sl["uuid"],
            organization=org,
            performed_by=_user(sl["performed_by"]),
            item=IngredientStock.objects.get(uuid=sl["ingredient"]),
            change_quantity=sl["change_quantity"],
            reason=sl["reason"],
            revenue=Decimal(sl["revenue"]),
            cost=Decimal(sl["cost"]),
            note=sl["note"],
            sale=sale,
        )
        # keep central's stock cache current; queryset.update() intentionally
        # bypasses save() AND the catalog-version bump signal
        IngredientStock.objects.filter(uuid=sl["ingredient"]).update(
            quantity=F("quantity") + sl["change_quantity"]
        )
    # auto_now_add stamped "now" on insert — restore the real till time
    # (queryset.update() bypasses auto_now_add)
    Sale.objects.filter(pk=sale.pk).update(created_at=p["sold_at"])
    for sl in p["stock_logs"]:
        StockLog.objects.filter(uuid=sl["uuid"]).update(created_at=sl["created_at"])
    return "ok"


# ══════════════════ STOCK ADJUSTMENTS, no sale (fill_stock etc.) ══════════════════


def freeze_stock_adjust(log):
    ing = log.item
    return {
        "log": {
            "uuid": str(log.uuid),
            "performed_by": log.performed_by.username if log.performed_by else None,
            "ingredient": str(ing.uuid),
            "change_quantity": log.change_quantity,
            "reason": log.reason,
            "revenue": str(log.revenue),
            "cost": str(log.cost),
            "note": log.note,
            "created_at": log.created_at.isoformat(),
        },
        "ingredient": {
            "uuid": str(ing.uuid),
            "name": ing.name,
            "wholesale_price": str(ing.wholesale_price),
            "retail_price": str(ing.retail_price),
            "added_as": ing.added_as or "",
            "item_id": ing.item_id,
        },
    }


def enqueue_stock_adjust(log):
    enqueue("stock_adjust", freeze_stock_adjust(log))


@transaction.atomic
def thaw_stock_adjust(p, org):
    if StockLog.objects.filter(uuid=p["log"]["uuid"]).exists():
        return "duplicate"
    i = p["ingredient"]
    ing = IngredientStock.objects.get_or_create(
        uuid=i["uuid"],
        defaults={
            "organization": org,
            "name": i["name"],
            "wholesale_price": Decimal(i["wholesale_price"]),
            "retail_price": Decimal(i["retail_price"]),
            "added_as": i["added_as"] or None,
            "item_id": i["item_id"],
        },
    )[0]
    log = StockLog.objects.create(
        uuid=p["log"]["uuid"],
        organization=org,
        performed_by=_user(p["log"]["performed_by"]),
        item=ing,
        change_quantity=p["log"]["change_quantity"],
        reason=p["log"]["reason"],
        revenue=Decimal(p["log"]["revenue"]),
        cost=Decimal(p["log"]["cost"]),
        note=p["log"]["note"],
    )
    IngredientStock.objects.filter(pk=ing.pk).update(
        quantity=F("quantity") + p["log"]["change_quantity"]
    )
    StockLog.objects.filter(pk=log.pk).update(created_at=p["log"]["created_at"])
    return "ok"


# ══════════════════ USERLOG (audit) ══════════════════
# ⚠⚠ ADJUST the field names to your actual UserLog — I haven't seen users/models.py
def freeze_userlog(log):
    return {
        "uuid": str(log.uuid),
        "device_id": log.device_id,
        "username": log.user.username if log.user_id else None,
        "reason": log.reason,
        "user_role": log.user_role,
        "notes": log.notes,
        "details": log.details,
        "created_at": log.created_at.isoformat(),
    }


def enqueue_userlog(log):
    enqueue("userlog", freeze_userlog(log))


@transaction.atomic
def thaw_userlog(p, org):
    if UserLog.objects.filter(uuid=p["uuid"]).exists():
        return "duplicate"
    user = _user(p["username"])
    if user is None:
        return "error"  # unknown user centrally → stays queued, visible in the badge
    log = UserLog.objects.create(
        uuid=p["uuid"],
        device_id=p["device_id"],
        reason=p["reason"],
        user=user,
        organization=org,
        user_role=p["user_role"],
        notes=p["notes"],
        details=p["details"],
    )
    UserLog.objects.filter(pk=log.pk).update(created_at=p["created_at"])
    return "ok"


THAWERS = {
    "sale": thaw_sale,
    "stock_adjust": thaw_stock_adjust,
    "userlog": thaw_userlog,
}


# ══════════════════ CATALOG SNAPSHOT (central → terminal) ══════════════════


def catalog_snapshot(org):
    return {
        "categories": [
            {
                "uuid": str(c.uuid),
                "name": c.name,
                "identifier": c.identifier,
                "description": c.description,
            }
            for c in Category.objects.filter(organization=org)
        ],
        "ingredients": [
            {
                "uuid": str(s.uuid),
                "name": s.name,
                "quantity": str(s.quantity),
                "wholesale_price": str(s.wholesale_price),
                "retail_price": str(s.retail_price),
                "added_as": s.added_as or "",
                "item_id": s.item_id,
            }
            for s in IngredientStock.objects.filter(organization=org)
        ],
        "items": [
            {
                "uuid": str(i.uuid),
                "name": i.name,
                "sku": i.sku,
                "category": str(i.category.uuid) if i.category_id else None,
                "cost_price": str(i.cost_price),
                "retail_price": str(i.retail_price),
                "wholesale_price": str(i.wholesale_price),
            }
            for i in Item.objects.filter(organization=org).select_related("category")
        ],
        "item_ingredients": [
            {
                "uuid": str(r.uuid),
                "item": str(r.item.uuid),
                "ingredient": str(r.ingredient.uuid),
                "quantity": str(r.quantity) if r.quantity is not None else None,
            }
            for r in ItemIngredient.objects.filter(
                item__organization=org
            ).select_related("item", "ingredient")
        ],
        "bundles": [
            {
                "uuid": str(b.uuid),
                "name": b.name,
                "price": str(b.price),
                "active": b.active,
                "items": [
                    {"item": str(bi.item.uuid), "quantity": str(bi.quantity)}
                    for bi in b.bundleitem_set.select_related("item")
                ],
            }
            for b in Bundle.objects.filter(organization=org)
        ],
    }


@transaction.atomic
def apply_catalog(data):
    # 0a. Organization — keep central's pk so every FK matches
    org = Organization.objects.update_or_create(
        pk=data["organization"]["pk"],
        defaults={
            "name": data["organization"]["name"],
            "slug": data["organization"]["slug"],
            "is_active": data["organization"]["is_active"],
        },
    )[0]

    # 0b. Staff: User + membership in THIS org.
    #     password is a HASH → offline login works; role drives your decorators offline
    User = get_user_model()
    for u in data["users"]:
        user = User.objects.update_or_create(
            username=u["username"],
            defaults={
                "email": u["email"],
                "password": u["password"],
                "first_name": u["first_name"],
                "last_name": u["last_name"],
                "is_active": u["is_active"],
                "is_staff": u["is_staff"],
                "is_superuser": u["is_superuser"],
            },
        )[0]
        OrganizationMembership.objects.update_or_create(
            user=user,
            organization=org,
            defaults={"role": u["role"], "is_default": u["is_default"]},
        )

    # 0c. Receipt/store settings — receipts must print correctly offline
    if data["settings"]:
        Settings.objects.update_or_create(organization=org, defaults=data["settings"])
    # 1. Categories
    for c in data["categories"]:
        Category.objects.update_or_create(
            uuid=c["uuid"],
            defaults={
                "organization": org,
                "name": c["name"],
                "identifier": c["identifier"],
                "description": c["description"],
            },
        )

    # 2. Ingredient levels — central's numbers already include this till's pushed
    #    deltas, because the engine PUSHES before it PULLS
    for s in data["ingredients"]:
        IngredientStock.objects.update_or_create(
            uuid=s["uuid"],
            defaults={
                "organization": org,
                "name": s["name"],
                "quantity": Decimal(s["quantity"]),
                "wholesale_price": Decimal(s["wholesale_price"]),
                "retail_price": Decimal(s["retail_price"]),
                "added_as": s["added_as"] or None,
                "item_id": s["item_id"],
            },
        )

    # 3. Items — TRAP: Item.save() recomputes wholesale_price from ingredients,
    #    which aren't linked yet (sum([]) == 0 would wipe it). So create with 0,
    #    then set the real value via queryset.update(), which bypasses save().
    for i in data["items"]:
        Item.objects.update_or_create(
            uuid=i["uuid"],
            defaults={
                "organization": org,
                "name": i["name"],
                "sku": i["sku"],
                "category": (
                    Category.objects.filter(uuid=i["category"]).first()
                    if i["category"]
                    else None
                ),
                "cost_price": Decimal(i["cost_price"]),
                "retail_price": Decimal(i["retail_price"]),
                "wholesale_price": Decimal(0),
            },
        )
    for i in data["items"]:
        Item.objects.filter(uuid=i["uuid"]).update(
            wholesale_price=Decimal(i["wholesale_price"])
        )

    # 4. Recipes + prune ones removed centrally
    for r in data["item_ingredients"]:
        ItemIngredient.objects.update_or_create(
            uuid=r["uuid"],
            defaults={
                "item": Item.objects.get(uuid=r["item"]),
                "ingredient": IngredientStock.objects.get(uuid=r["ingredient"]),
                "quantity": (
                    Decimal(r["quantity"]) if r["quantity"] is not None else None
                ),
            },
        )
    ItemIngredient.objects.filter(item__organization=org).exclude(
        uuid__in=[r["uuid"] for r in data["item_ingredients"]]
    ).delete()

    # 5. Bundles — BundleItem has no uuid, so replace each bundle's rows
    for b in data["bundles"]:
        bundle, _ = Bundle.objects.update_or_create(
            uuid=b["uuid"],
            defaults={
                "organization": org,
                "name": b["name"],
                "price": Decimal(b["price"]),
                "active": b["active"],
            },
        )
        BundleItem.objects.filter(bundle=bundle).delete()
        BundleItem.objects.bulk_create(
            [
                BundleItem(
                    bundle=bundle,
                    item=Item.objects.get(uuid=bi["item"]),
                    quantity=Decimal(bi["quantity"]),
                )
                for bi in b["items"]
            ]
        )
    return org
