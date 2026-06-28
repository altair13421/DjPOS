from django.db import migrations


def backfill_default_organization(apps, schema_editor):
    Organization = apps.get_model("users", "Organization")
    OrganizationMembership = apps.get_model("users", "OrganizationMembership")
    Settings = apps.get_model("users", "Settings")
    UserLog = apps.get_model("users", "UserLog")
    User = apps.get_model("auth", "User")
    Customer = apps.get_model("pos", "Customer")
    Sale = apps.get_model("pos", "Sale")
    Category = apps.get_model("inventory", "Category")
    Item = apps.get_model("inventory", "Item")
    Bundle = apps.get_model("inventory", "Bundle")
    IngredientStock = apps.get_model("inventory", "IngredientStock")
    StockLog = apps.get_model("inventory", "StockLog")

    org, _ = Organization.objects.get_or_create(
        slug="default",
        defaults={"name": "Default Organization"},
    )

    for model in (
        Customer,
        Sale,
        Category,
        Item,
        Bundle,
        IngredientStock,
        StockLog,
        UserLog,
    ):
        model.objects.filter(organization__isnull=True).update(organization=org)

    for settings in Settings.objects.filter(organization__isnull=True):
        settings.organization = org
        settings.save()

    if not Settings.objects.filter(organization=org).exists():
        Settings.objects.create(
            organization=org,
            store_name="DJPOS",
            store_address="",
        )

    for user in User.objects.all():
        if user.is_superuser or user.is_staff:
            role = "owner"
        else:
            role = "cashier"
        OrganizationMembership.objects.get_or_create(
            user=user,
            organization=org,
            defaults={"role": role, "is_default": True},
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_organization_alter_settings_store_address_and_more"),
        ("pos", "0005_customer_organization_sale_created_by_and_more"),
        ("inventory", "0009_bundle_organization_category_organization_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_default_organization, noop),
    ]
