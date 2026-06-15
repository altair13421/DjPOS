from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import (
    Category,
    IngredientStock,
    Item,
    ItemIngredient,
    Bundle,
    BundleItem,
)
from inventory.choices import StockAddedAs

class Command(BaseCommand):
    help = "Populate DB with example categories, ingredient stocks, items, bundles, and direct-consumption items."

    @transaction.atomic
    def handle(self, *args, **options):
        created = {"categories":0, "ingredients":0, "items":0, "item_ingredients":0, "bundles":0, "bundle_items":0, "direct_items":0}

        # --- categories (same as before) ---
        cats = [
            {"name":"Bakery", "identifier":"BAKE", "description":"Baked goods"},
            {"name":"Beverages", "identifier":"BEV", "description":"Drinks"},
            {"name":"Condiments", "identifier":"COND", "description":"Sauces & extras"},
        ]
        categories = {}
        for c in cats:
            obj, ok = Category.objects.get_or_create(identifier=c["identifier"], defaults={"name":c["name"], "description":c["description"]})
            categories[c["identifier"]] = obj
            if ok:
                created["categories"] += 1

        # --- ingredient stocks (same as before) ---
        ingr_data = [
            {"name":"Flour", "quantity":Decimal("100.00"), "wholesale_price":Decimal("20.00"), "retail_price":Decimal("25.00")},
            {"name":"Sugar", "quantity":Decimal("50.00"), "wholesale_price":Decimal("30.00"), "retail_price":Decimal("40.00")},
            {"name":"Butter", "quantity":Decimal("20.00"), "wholesale_price":Decimal("200.00"), "retail_price":Decimal("250.00")},
            {"name":"Milk", "quantity":Decimal("200.00"), "wholesale_price":Decimal("60.00"), "retail_price":Decimal("80.00")},
            {"name":"Coffee Beans", "quantity":Decimal("30.00"), "wholesale_price":Decimal("400.00"), "retail_price":Decimal("500.00")},
            {"name":"Tea Leaves", "quantity":Decimal("40.00"), "wholesale_price":Decimal("150.00"), "retail_price":Decimal("200.00")},
            {"name":"Ketchup", "quantity":Decimal("80.00"), "wholesale_price":Decimal("50.00"), "retail_price":Decimal("70.00")},
            {"name":"Yeast", "quantity":Decimal("10.00"), "wholesale_price":Decimal("120.00"), "retail_price":Decimal("150.00")},
        ]
        ingredients = {}
        for d in ingr_data:
            obj, ok = IngredientStock.objects.get_or_create(name=d["name"], defaults={
                "quantity": d["quantity"],
                "wholesale_price": d["wholesale_price"],
                "retail_price": d["retail_price"],
            })
            ingredients[d["name"]] = obj
            if ok:
                created["ingredients"] += 1

        # --- composed items (same as before) ---
        items_data = [
            {"name":"White Bread", "sku":"BAKE-001", "category":categories["BAKE"], "cost_price":Decimal("50.00"), "retail_price":Decimal("80.00"), "wholesale_price":Decimal("65.00")},
            {"name":"Croissant", "sku":"BAKE-002", "category":categories["BAKE"], "cost_price":Decimal("60.00"), "retail_price":Decimal("100.00"), "wholesale_price":Decimal("80.00")},
            {"name":"Latte", "sku":"BEV-001", "category":categories["BEV"], "cost_price":Decimal("70.00"), "retail_price":Decimal("150.00"), "wholesale_price":Decimal("110.00")},
            {"name":"Black Tea", "sku":"BEV-002", "category":categories["BEV"], "cost_price":Decimal("20.00"), "retail_price":Decimal("60.00"), "wholesale_price":Decimal("35.00")},
            {"name":"Ketchup Bottle", "sku":"COND-001", "category":categories["COND"], "cost_price":Decimal("80.00"), "retail_price":Decimal("140.00"), "wholesale_price":Decimal("100.00")},
            {"name":"Butter Pack", "sku":"COND-002", "category":categories["COND"], "cost_price":Decimal("180.00"), "retail_price":Decimal("250.00"), "wholesale_price":Decimal("200.00")},
        ]
        items = {}
        for d in items_data:
            obj, ok = Item.objects.get_or_create(sku=d["sku"], defaults={
                "name": d["name"],
                "category": d["category"],
                "cost_price": d["cost_price"],
                "retail_price": d["retail_price"],
                "wholesale_price": d["wholesale_price"],
            })
            items[d["sku"]] = obj
            if ok:
                created["items"] += 1

        # --- ItemIngredient relations for composed items (same as before) ---
        ii_data = [
            {"item_sku":"BAKE-001", "ingredient":"Flour", "quantity":Decimal("0.50")},
            {"item_sku":"BAKE-001", "ingredient":"Yeast", "quantity":Decimal("0.02")},
            {"item_sku":"BAKE-002", "ingredient":"Flour", "quantity":Decimal("0.30")},
            {"item_sku":"BAKE-002", "ingredient":"Butter", "quantity":Decimal("0.10")},
            {"item_sku":"BEV-001", "ingredient":"Coffee Beans", "quantity":Decimal("0.02")},
            {"item_sku":"BEV-001", "ingredient":"Milk", "quantity":Decimal("0.15")},
            {"item_sku":"BEV-002", "ingredient":"Tea Leaves", "quantity":Decimal("0.01")},
            {"item_sku":"COND-001", "ingredient":"Ketchup", "quantity":Decimal("0.40")},
            {"item_sku":"COND-002", "ingredient":"Butter", "quantity":Decimal("0.50")},
        ]
        for rel in ii_data:
            item = items.get(rel["item_sku"])
            ing = ingredients.get(rel["ingredient"])
            if not item or not ing:
                continue
            obj, ok = ItemIngredient.objects.get_or_create(item=item, ingredient=ing, defaults={"quantity": rel["quantity"]})
            if ok:
                created["item_ingredients"] += 1

        # --- Direct-consumption items ---
        # These are items sold as single sealed/finished products (quantity consumed = 1).
        direct_items = [
            {"name":"Sealed Softdrink 330ml", "sku":"BEV-SD-001", "category": categories["BEV"], "retail_price": Decimal("120.00"), "wholesale_price": Decimal("90.00"), "quantity": Decimal('20')},
            {"name":"Packaged Bread Loaf", "sku":"BAKE-PB-001", "category": categories["BAKE"], "retail_price": Decimal("150.00"), "wholesale_price": Decimal("110.00"), "quantity":  Decimal("10")},
        ]
        for d in direct_items:
            # Ensure IngredientStock exists with same name/prices (acts as the consumed unit)
            ing_obj, ing_created = IngredientStock.objects.get_or_create(
                name=d["name"],
                defaults={
                    "quantity": d["quantity"],
                    "wholesale_price": d["wholesale_price"],
                    "retail_price": d["retail_price"],
                    "added_as": StockAddedAs.ITEM,
                },
            )
            if ing_created:
                created["ingredients"] += 1

            # Ensure Item exists
            item_obj, item_created = Item.objects.get_or_create(
                sku=d["sku"],
                defaults={
                    "name": d["name"],
                    "category": d["category"],
                    "cost_price": d["wholesale_price"],
                    "retail_price": d["retail_price"],
                    "wholesale_price": d["wholesale_price"],
                },
            )
            ing_obj.item_id = item_obj.id
            if item_created:
                created["items"] += 1
                created["direct_items"] += 1

            # Link Item -> IngredientStock with quantity = 1 (idempotent)
            ii_obj, ii_created = ItemIngredient.objects.get_or_create(
                item=item_obj,
                ingredient=ing_obj,
                defaults={"quantity": Decimal("1")},
            )
            if ii_created:
                created["item_ingredients"] += 1

        # --- Bundles (same as before) ---
        bundles_data = [
            {"name":"Breakfast Combo", "price":Decimal("200.00"), "items":[("BAKE-001", Decimal("1")), ("BEV-001", Decimal("1"))]},
            {"name":"Snack Pack", "price":Decimal("300.00"), "items":[("BAKE-002", Decimal("2")), ("COND-001", Decimal("1"))]},
        ]
        for b in bundles_data:
            bundle_obj, ok = Bundle.objects.get_or_create(name=b["name"], defaults={"price": b["price"], "active": True})
            if ok:
                created["bundles"] += 1
            for sku, qty in b["items"]:
                item = items.get(sku)
                if not item:
                    continue
                bi_obj, bi_ok = BundleItem.objects.get_or_create(bundle=bundle_obj, item=item, defaults={"quantity": qty})
                if bi_ok:
                    created["bundle_items"] += 1

        # Summary
        self.stdout.write(self.style.SUCCESS(
            "Populate complete: categories=%d, ingredients=%d, items=%d, direct_items=%d, item_ingredients=%d, bundles=%d, bundle_items=%d" % (
                created.get("categories",0),
                created.get("ingredients",0),
                created.get("items",0),
                created.get("direct_items",0),
                created.get("item_ingredients",0),
                created.get("bundles",0),
                created.get("bundle_items",0),
            )
        ))

