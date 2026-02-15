import pytest
from decimal import Decimal
from inventory.models import Item, StockLog
from inventory.choices import StockChangeReason
from utils.stock_manager import StockManager

@pytest.mark.django_db
class TestStockManager:
    def test_deduct_stock_success(self):
        item = Item.objects.create(name="Test Item", quantity=10, cost_price=5, sku="TEST-1")
        StockManager.deduct_stock(item, 2, reason=StockChangeReason.SALE)
        
        item.refresh_from_db()
        assert item.quantity == 8
        
        log = StockLog.objects.last()
        assert log.item == item
        assert log.change_quantity == -2
        assert log.reason == StockChangeReason.SALE

    def test_insufficient_stock(self):
        item = Item.objects.create(name="Low Stock Item", quantity=1, sku="TEST-2")
        with pytest.raises(ValueError):
            StockManager.deduct_stock(item, 2)

    def test_restock_item(self):
        item = Item.objects.create(name="Restock Item", quantity=5, sku="TEST-3")
        StockManager.restock_item(item, 5, reason=StockChangeReason.RESTOCK)
        
        item.refresh_from_db()
        assert item.quantity == 10
        
        log = StockLog.objects.last()
        assert log.change_quantity == 5
        assert log.reason == StockChangeReason.RESTOCK
