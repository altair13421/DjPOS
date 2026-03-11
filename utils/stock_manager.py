from django.db import transaction
from inventory.models import StockLog
from inventory.choices import StockChangeReason

class StockManager:
    @staticmethod
    @transaction.atomic
    def deduct_stock(item, quantity, reason=StockChangeReason.SALE, note="", revenue=0, cost=0):
        """Deduct stock from an item."""
        if item.quantity < quantity:
            raise ValueError(f"Insufficient stock for {item.name}. Required: {quantity}, Available: {item.quantity}")
        
        item.quantity -= quantity
        item.save()
        
        StockLog.objects.create(
            item=item,
            change_quantity=-quantity,
            reason=reason,
            revenue=revenue,
            cost=cost,
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
                
                # Standalone item: revenue is the unit_price of the cart line, cost is item's wholesale_price
                revenue = cart_item.unit_price * cart_item.quantity
                cost = item.wholesale_price * cart_item.quantity
                
                StockManager.deduct_stock(
                    item=item,
                    quantity=cart_item.quantity,
                    reason=StockChangeReason.SALE,
                    note=f"Sale #{sale.id}",
                    revenue=revenue,
                    cost=cost
                )
                item.refresh_from_db()
                cart_item.stock_after = item.quantity
                cart_item.save(update_fields=['stock_after'])
            elif cart_item.bundle_id:
                # Pro-rate the revenue for bundle items based on retail_price
                bundle_items = cart_item.bundle.bundleitem_set.select_related('item').all()
                total_retail = sum(bi.item.retail_price * bi.quantity for bi in bundle_items)
                
                for bi in bundle_items:
                    qty = bi.quantity * cart_item.quantity
                    
                    if total_retail > 0:
                        item_retail_share = (bi.item.retail_price * bi.quantity) / total_retail
                    else:
                        item_retail_share = 0 # Fallback if items are free
                        
                    revenue = (cart_item.unit_price * cart_item.quantity) * item_retail_share
                    cost = bi.item.wholesale_price * qty
                    
                    StockManager.deduct_stock(
                        item=bi.item,
                        quantity=qty,
                        reason=StockChangeReason.SALE,
                        note=f"Sale #{sale.id} (Bundle)",
                        revenue=revenue,
                        cost=cost
                    )
