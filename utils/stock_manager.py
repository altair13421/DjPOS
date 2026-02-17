from django.db import transaction
from inventory.models import StockLog
from inventory.choices import StockChangeReason

class StockManager:
    @staticmethod
    @transaction.atomic
    def deduct_stock(item, quantity, reason=StockChangeReason.SALE, note=""):
        """Deduct stock from an item."""
        if item.quantity < quantity:
            raise ValueError(f"Insufficient stock for {item.name}. Required: {quantity}, Available: {item.quantity}")
        
        item.quantity -= quantity
        item.save()
        
        StockLog.objects.create(
            item=item,
            change_quantity=-quantity,
            reason=reason,
            note=note
        )

    @staticmethod
    @transaction.atomic
    def restock_item(item, quantity, reason=StockChangeReason.RESTOCK, note=""):
        """Add stock to an item."""
        item.quantity += quantity
        item.save()
        
        StockLog.objects.create(
            item=item,
            change_quantity=quantity,
            reason=reason,
            note=note
        )

    @staticmethod
    @transaction.atomic
    def process_sale(sale):
        """Process stock deduction for a completed sale (items and bundles)."""
        cart_items = sale.sale_items.select_related('item', 'bundle').prefetch_related(
            'bundle__bundleitem_set__item'
        ).all()
        for cart_item in cart_items:
            if cart_item.item_id:
                item = cart_item.item
                cart_item.stock_before = item.quantity
                cart_item.save(update_fields=['stock_before'])
                StockManager.deduct_stock(
                    item=item,
                    quantity=cart_item.quantity,
                    reason=StockChangeReason.SALE,
                    note=f"Sale #{sale.id}"
                )
                item.refresh_from_db()
                cart_item.stock_after = item.quantity
                cart_item.save(update_fields=['stock_after'])
            elif cart_item.bundle_id:
                for bi in cart_item.bundle.bundleitem_set.select_related('item').all():
                    qty = bi.quantity * cart_item.quantity
                    StockManager.deduct_stock(
                        item=bi.item,
                        quantity=qty,
                        reason=StockChangeReason.SALE,
                        note=f"Sale #{sale.id} (Bundle)"
                    )
