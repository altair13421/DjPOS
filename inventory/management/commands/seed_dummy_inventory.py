from decimal import Decimal

from django.core.management.base import BaseCommand

from inventory.models import Bundle, BundleItem, Item, Category


class Command(BaseCommand):
    help = (
        "Create dummy inventory items (ingredient/non-ingredient, active/inactive) "
        "and sample bundles that pair well with ingredients."
    )

    def handle(self, *args, **options):
        items_by_sku = self._seed_items()
        self._seed_bundles(items_by_sku)
        self.stdout.write(self.style.SUCCESS("Dummy inventory seed completed."))

    def _seed_items(self):
        category = Category.objects.create(
            name="DummyObjects",
            identifier="DUM",
            description="Dummy Objects auto added"
        )

        item_specs = [
            {
                "sku": "DUM-ING-ACT-001",
                "name": "Tomato",
                "is_ingredient": True,
                "is_active": True,
                "quantity": Decimal("50"),
                "cost_price": Decimal("40"),
                "retail_price": Decimal("80"),
                "wholesale_price": Decimal("70"),
            },
            {
                "sku": "DUM-ING-ACT-003",
                "name": "Chicken",
                "is_ingredient": True,
                "is_active": True,
                "quantity": Decimal("20"),
                "cost_price": Decimal("560"),
                "retail_price": Decimal("560"),
                "wholesale_price": Decimal("500"),
            },
            {
                "sku": "DUM-ING-ACT-002",
                "name": "Cheddar Cheese",
                "is_ingredient": True,
                "is_active": True,
                "quantity": Decimal("30"),
                "cost_price": Decimal("120"),
                "retail_price": Decimal("200"),
                "wholesale_price": Decimal("180"),
            },
            {
                "sku": "DUM-ING-INACT-001",
                "name": "Basil Leaves",
                "is_ingredient": True,
                "is_active": False,
                "quantity": Decimal("0"),
                "cost_price": Decimal("25"),
                "retail_price": Decimal("50"),
                "wholesale_price": Decimal("40"),
            },
            {
                "sku": "DUM-PRD-ACT-001",
                "name": "Margherita Pizza",
                "is_ingredient": False,
                "is_active": True,
                "quantity": Decimal("12"),
                "cost_price": Decimal("350"),
                "retail_price": Decimal("650"),
                "wholesale_price": Decimal("600"),
            },
            {
                "sku": "DUM-PRD-INACT-001",
                "name": "Chocolate Cake Slice",
                "is_ingredient": False,
                "is_active": False,
                "quantity": Decimal("0"),
                "cost_price": Decimal("90"),
                "retail_price": Decimal("180"),
                "wholesale_price": Decimal("150"),
            },
            {
                "sku": "DUM-PRD-ACT-002",
                "name": "Garlic Bread",
                "is_ingredient": False,
                "is_active": True,
                "quantity": Decimal("20"),
                "cost_price": Decimal("70"),
                "retail_price": Decimal("130"),
                "wholesale_price": Decimal("110"),
            },
        ]

        items_by_sku = {}
        for spec in item_specs:
            sku = spec["sku"]
            defaults = {k: v for k, v in spec.items() if k != "sku"}
            item, created = Item.objects.update_or_create(sku=sku, defaults=defaults)
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} item: {item.name} [{sku}]")
            items_by_sku[sku] = item

        return items_by_sku

    def _seed_bundles(self, items_by_sku):
        bundle_specs = [
            {
                "name": "Fresh Pizza Prep Pack",
                "price": Decimal("420"),
                "active": True,
                "components": [
                    ("DUM-ING-ACT-001", Decimal("3")),
                    ("DUM-ING-ACT-002", Decimal("2")),
                ],
            },
            {
                "name": "Chicken Zinger Burger",
                "price": Decimal("420"),
                "active": True,
                "components": [
                    ("DUM-ING-ACT-003", Decimal("0.3")),
                    ("DUM-ING-ACT-002", Decimal("1")),
                ]
            },
            {
                "name": "Italian Herb Combo",
                "price": Decimal("180"),
                "active": False,
                "components": [
                    ("DUM-ING-ACT-001", Decimal("1")),
                    ("DUM-ING-INACT-001", Decimal("2")),
                ],
            },
            {
                "name": "Cheesy Starter Mix",
                "price": Decimal("320"),
                "active": True,
                "components": [
                    ("DUM-ING-ACT-002", Decimal("1.5")),
                    ("DUM-ING-ACT-001", Decimal("2")),
                ],
            },
        ]

        for spec in bundle_specs:
            bundle, created = Bundle.objects.get_or_create(
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
                BundleItem.objects.create(bundle=bundle, item=item, quantity=quantity)

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} bundle: {bundle.name}")
