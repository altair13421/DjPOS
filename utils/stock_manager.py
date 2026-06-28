from django.db import transaction
from inventory.models import StockLog, IngredientStock
from inventory.choices import StockChangeReason
from pos.models import Sale


class StockManager:
    @staticmethod
    @transaction.atomic
    def deduct_stock(
        item: IngredientStock,
        quantity,
        reason=StockChangeReason.SALE,
        note="",
        revenue=0,
        cost=0,
        sale: Sale = None,
        performed_by=None,
    ):
        """Deduct stock from an item."""
        if item.quantity < quantity:
            raise ValueError(f"Insufficient stock for {item.name}. Required: {quantity}, Available: {item.quantity}")

        item.quantity -= quantity
        item.save()

        StockLog.objects.create(
            item=item,
            organization=item.organization,
            performed_by=performed_by,
            change_quantity=-quantity,
            reason=reason,
            revenue=revenue,
            cost=cost,
            note=note,
            sale=sale,
        )

    @staticmethod
    @transaction.atomic
    def restock_item(
        item: IngredientStock,
        quantity,
        reason=StockChangeReason.RESTOCK,
        note="",
        performed_by=None,
    ):
        """Add stock to an item."""
        item.quantity += quantity
        item.save()

        StockLog.objects.create(
            item=item,
            organization=item.organization,
            performed_by=performed_by,
            change_quantity=quantity,
            reason=reason,
            note=note,
        )

    @staticmethod
    @transaction.atomic
    def process_sale(sale, performed_by=None):
        """Process stock deduction for a completed sale (items and bundles)."""
        cart_items = sale.sale_items.select_related('item', 'bundle').prefetch_related(
            'bundle__bundleitem_set__item__ingredients'
        ).all()
        for cart_item in cart_items:
            if cart_item.item_id:
                item = cart_item.item
                cart_item.stock_before = item.availability_count
                cart_item.save(update_fields=['stock_before'])

                revenue = cart_item.unit_price * cart_item.quantity
                cost = item.wholesale_price * cart_item.quantity
                for ingredient in item.itemingredient_set.all():
                    StockManager.deduct_stock(
                        item=ingredient.ingredient,
                        quantity=cart_item.quantity * ingredient.quantity,
                        reason=StockChangeReason.SALE,
                        note=f"Sale #{sale.id} | StockBefore: {ingredient.ingredient.quantity}| StockAfter: {ingredient.ingredient.quantity - cart_item.quantity*ingredient.quantity}",
                        revenue=revenue,
                        cost=cost,
                        sale=sale,
                        performed_by=performed_by,
                    )
                item.refresh_from_db()
                cart_item.stock_after = item.availability_count
                cart_item.save(update_fields=['stock_after'])
            elif cart_item.bundle_id:
                bundle_items = cart_item.bundle.bundleitem_set.select_related('item').all()
                total_retail = sum(bi.item.retail_price * bi.quantity for bi in bundle_items)

                for bi in bundle_items:
                    qty = bi.quantity * cart_item.quantity

                    if total_retail > 0:
                        item_retail_share = (bi.item.retail_price * bi.quantity) / total_retail
                    else:
                        item_retail_share = 0

                    revenue = (cart_item.unit_price * cart_item.quantity) * item_retail_share
                    cost = bi.item.wholesale_price * qty
                    for ingredient in bi.item.itemingredient_set.all():
                        StockManager.deduct_stock(
                            item=ingredient.ingredient,
                            quantity=qty * ingredient.quantity,
                            reason=StockChangeReason.SALE,
                            note=f"Sale #{sale.id} (Bundle)",
                            revenue=revenue,
                            cost=cost,
                            sale=sale,
                            performed_by=performed_by,
                        )
