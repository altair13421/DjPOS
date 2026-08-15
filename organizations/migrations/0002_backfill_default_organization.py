# Data migration: default organization, backfill, ceiling-round quantities

from decimal import Decimal
from math import ceil

from django.conf import settings
from django.db import migrations
from django.db.models import Q


def forwards(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    OrganizationMembership = apps.get_model("organizations", "OrganizationMembership")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Category = apps.get_model("inventory", "Category")
    Item = apps.get_model("inventory", "Item")
    Bundle = apps.get_model("inventory", "Bundle")
    BundleItem = apps.get_model("inventory", "BundleItem")
    Customer = apps.get_model("pos", "Customer")
    Sale = apps.get_model("pos", "Sale")

    org, _ = Organization.objects.get_or_create(
        slug="default-organization",
        defaults={"name": "Default Organization"},
    )

    Category.objects.filter(organization__isnull=True).update(organization=org)
    Item.objects.filter(organization__isnull=True).update(organization=org)
    Bundle.objects.filter(organization__isnull=True).update(organization=org)
    Customer.objects.filter(organization__isnull=True).update(organization=org)
    Sale.objects.filter(organization__isnull=True).update(organization=org)

    for user in User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)):
        OrganizationMembership.objects.get_or_create(
            organization=org,
            user=user,
            defaults={"role": "owner"},
        )

    for item in Item.objects.all():
        qty = item.quantity
        if qty is None:
            continue
        rounded = int(ceil(Decimal(str(qty))))
        if Decimal(str(qty)) != Decimal(rounded):
            item.quantity = rounded
            item.save(update_fields=["quantity"])

    for bi in BundleItem.objects.all():
        qty = bi.quantity
        if qty is None:
            continue
        rounded = int(ceil(Decimal(str(qty))))
        if Decimal(str(qty)) != Decimal(rounded):
            bi.quantity = rounded
            bi.save(update_fields=["quantity"])

    # Ensure org-scoped unique fields are populated before constraints.
    for category in Category.objects.filter(Q(identifier="") | Q(identifier__isnull=True)):
        base = (category.name or "CAT")[:4].upper() or "CAT"
        candidate = base
        n = 2
        while Category.objects.filter(
            organization=category.organization, identifier=candidate
        ).exclude(pk=category.pk).exists():
            candidate = f"{base}{n}"
            n += 1
        category.identifier = candidate
        category.save(update_fields=["identifier"])

    for item in Item.objects.filter(Q(sku="") | Q(sku__isnull=True)):
        candidate = f"ITEM-{item.pk}"
        n = 2
        while Item.objects.filter(
            organization=item.organization, sku=candidate
        ).exclude(pk=item.pk).exists():
            candidate = f"ITEM-{item.pk}-{n}"
            n += 1
        item.sku = candidate
        item.save(update_fields=["sku"])


def backwards(apps, schema_editor):
    OrganizationMembership = apps.get_model("organizations", "OrganizationMembership")
    OrganizationMembership.objects.filter(
        organization__slug="default-organization"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0007_add_organization_nullable"),
        ("pos", "0003_add_organization_nullable"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
