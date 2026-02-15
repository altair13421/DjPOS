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
        """Process stock deduction for a completed sale."""
        # Iterate over directly related Sale items
        for cart_item in sale.sale_items.all():
            StockManager.deduct_stock(
                item=cart_item.item,
                quantity=cart_item.quantity,
                reason=StockChangeReason.SALE,
                note=f"Sale #{sale.id}"
            )
