from math import ceil

from django.core.management.base import BaseCommand, CommandError

from inventory.models import Bundle, BundleItem, Category, Item
from organizations.models import Organization


class Command(BaseCommand):
    help = (
        "Create dummy inventory items (ingredient/non-ingredient, active/inactive) "
        "and sample bundles for an organization."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization",
            default="default-organization",
            help="Organization slug to seed (default: default-organization)",
        )

    def handle(self, *args, **options):
        slug = options["organization"]
        try:
            organization = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist as exc:
            raise CommandError(f"Organization with slug '{slug}' not found.") from exc

        items_by_sku = self._seed_items(organization)
        self._seed_bundles(organization, items_by_sku)
        self.stdout.write(
            self.style.SUCCESS(f"Dummy inventory seed completed for {organization.name}.")
        )

    def _seed_items(self, organization):
        category, _ = Category.objects.get_or_create(
            organization=organization,
            identifier="DUM",
            defaults={
                "name": "DummyObjects",
                "description": "Dummy Objects auto added",
            },
        )

        item_specs = [
            {
                "sku": "DUM-ING-ACT-001",
                "name": "Tomato",
                "is_ingredient": True,
                "is_active": True,
                "quantity": 50,
                "reorder_level": 10,
                "cost_price": 40,
                "retail_price": 80,
                "wholesale_price": 70,
            },
            {
                "sku": "DUM-ING-ACT-003",
                "name": "Chicken",
                "is_ingredient": True,
                "is_active": True,
                "quantity": 20,
                "reorder_level": 5,
                "cost_price": 560,
                "retail_price": 560,
                "wholesale_price": 500,
            },
            {
                "sku": "DUM-ING-ACT-002",
                "name": "Cheddar Cheese",
                "is_ingredient": True,
                "is_active": True,
                "quantity": 30,
                "reorder_level": 8,
                "cost_price": 120,
                "retail_price": 200,
                "wholesale_price": 180,
            },
            {
                "sku": "DUM-ING-INACT-001",
                "name": "Basil Leaves",
                "is_ingredient": True,
                "is_active": False,
                "quantity": 0,
                "reorder_level": 5,
                "cost_price": 25,
                "retail_price": 50,
                "wholesale_price": 40,
            },
            {
                "sku": "DUM-PRD-ACT-001",
                "name": "Margherita Pizza",
                "is_ingredient": False,
                "is_active": True,
                "quantity": 12,
                "reorder_level": 3,
                "cost_price": 350,
                "retail_price": 650,
                "wholesale_price": 600,
            },
            {
                "sku": "DUM-PRD-INACT-001",
                "name": "Chocolate Cake Slice",
                "is_ingredient": False,
                "is_active": False,
                "quantity": 0,
                "reorder_level": 2,
                "cost_price": 90,
                "retail_price": 180,
                "wholesale_price": 150,
            },
            {
                "sku": "DUM-PRD-ACT-002",
                "name": "Garlic Bread",
                "is_ingredient": False,
                "is_active": True,
                "quantity": 20,
                "reorder_level": 5,
                "cost_price": 70,
                "retail_price": 130,
                "wholesale_price": 110,
            },
        ]

        items_by_sku = {}
        for spec in item_specs:
            sku = spec["sku"]
            defaults = {k: v for k, v in spec.items() if k != "sku"}
            defaults["organization"] = organization
            defaults["category"] = category
            item, created = Item.objects.update_or_create(
                organization=organization,
                sku=sku,
                defaults=defaults,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} item: {item.name} [{sku}]")
            items_by_sku[sku] = item

        return items_by_sku

    def _seed_bundles(self, organization, items_by_sku):
        bundle_specs = [
            {
                "name": "Fresh Pizza Prep Pack",
                "price": 420,
                "active": True,
                "components": [
                    ("DUM-ING-ACT-001", 3),
                    ("DUM-ING-ACT-002", 2),
                ],
            },
            {
                "name": "Chicken Zinger Burger",
                "price": 420,
                "active": True,
                "components": [
                    ("DUM-ING-ACT-003", 1),  # was 0.3; whole items only
                    ("DUM-ING-ACT-002", 1),
                ],
            },
            {
                "name": "Italian Herb Combo",
                "price": 180,
                "active": False,
                "components": [
                    ("DUM-ING-ACT-001", 1),
                    ("DUM-ING-INACT-001", 2),
                ],
            },
            {
                "name": "Cheesy Starter Mix",
                "price": 320,
                "active": True,
                "components": [
                    ("DUM-ING-ACT-002", 2),  # was 1.5; ceiling to whole items
                    ("DUM-ING-ACT-001", 2),
                ],
            },
        ]

        for spec in bundle_specs:
            bundle, created = Bundle.objects.get_or_create(
                organization=organization,
                name=spec["name"],
                defaults={"price": spec["price"], "active": spec["active"]},
            )
            if not created:
                bundle.price = spec["price"]
                bundle.active = spec["active"]
                bundle.save(update_fields=["price", "active", "updated_at"])

            BundleItem.objects.filter(bundle=bundle).delete()
            for sku, quantity in spec["components"]:
                item = items_by_sku.get(sku)
                if not item:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping missing item SKU {sku} for bundle {bundle.name}."
                        )
                    )
                    continue
                BundleItem.objects.create(
                    bundle=bundle,
                    item=item,
                    quantity=int(ceil(quantity)),
                )

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} bundle: {bundle.name}")
