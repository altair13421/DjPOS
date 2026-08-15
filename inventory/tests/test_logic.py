import pytest
from decimal import Decimal

from inventory.models import Item, StockLog, Bundle, BundleItem
from inventory.choices import StockChangeReason
from organizations.models import Organization
from utils.stock_manager import StockManager
from pos.models import Sale, CartItem


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Logic Org", slug="logic-org")


@pytest.mark.django_db
class TestStockManager:
    def test_deduct_stock_success(self, organization):
        item = Item.objects.create(
            organization=organization,
            name="Test Item",
            quantity=10,
            cost_price=5,
            sku="TEST-1",
        )
        StockManager.deduct_stock(item, 2, reason=StockChangeReason.SALE)

        item.refresh_from_db()
        assert item.quantity == 8

        log = StockLog.objects.last()
        assert log.item == item
        assert log.change_quantity == -2
        assert log.reason == StockChangeReason.SALE

    def test_insufficient_stock(self, organization):
        item = Item.objects.create(
            organization=organization, name="Low Stock Item", quantity=1, sku="TEST-2"
        )
        with pytest.raises(ValueError):
            StockManager.deduct_stock(item, 2)

    def test_restock_item(self, organization):
        item = Item.objects.create(
            organization=organization, name="Restock Item", quantity=5, sku="TEST-3"
        )
        StockManager.restock_item(item, 5, reason=StockChangeReason.RESTOCK)

        item.refresh_from_db()
        assert item.quantity == 10

        log = StockLog.objects.last()
        assert log.change_quantity == 5
        assert log.reason == StockChangeReason.RESTOCK


@pytest.mark.django_db
class TestProcessSaleWithBundle:
    def test_process_sale_deducts_bundle_components(self, organization):
        item1 = Item.objects.create(
            organization=organization, name="Bun", quantity=20, sku="BUN"
        )
        item2 = Item.objects.create(
            organization=organization, name="Patty", quantity=20, sku="PATTY"
        )
        bundle = Bundle.objects.create(
            organization=organization, name="Burger", price=Decimal("15")
        )
        BundleItem.objects.create(bundle=bundle, item=item1, quantity=1)
        BundleItem.objects.create(bundle=bundle, item=item2, quantity=1)

        sale = Sale.objects.create(organization=organization, total=Decimal("30"))
        CartItem.objects.create(
            sale=sale, bundle=bundle, item=None, quantity=2, unit_price=Decimal("15")
        )

        StockManager.process_sale(sale)

        item1.refresh_from_db()
        item2.refresh_from_db()
        assert item1.quantity == 18
        assert item2.quantity == 18

        logs = StockLog.objects.filter(reason=StockChangeReason.SALE).order_by("id")
        assert logs.count() >= 2
        change_qty = {log.item_id: log.change_quantity for log in logs}
        assert change_qty.get(item1.id) == -2
        assert change_qty.get(item2.id) == -2

    def test_process_sale_mixed_item_and_bundle(self, organization):
        item1 = Item.objects.create(
            organization=organization, name="Solo", quantity=10, sku="SOLO"
        )
        item2 = Item.objects.create(
            organization=organization, name="InBundle", quantity=10, sku="INB"
        )
        bundle = Bundle.objects.create(
            organization=organization, name="Pack", price=Decimal("5")
        )
        BundleItem.objects.create(bundle=bundle, item=item2, quantity=1)

        sale = Sale.objects.create(organization=organization, total=Decimal("15"))
        CartItem.objects.create(
            sale=sale, item=item1, bundle=None, quantity=3, unit_price=Decimal("2")
        )
        CartItem.objects.create(
            sale=sale, bundle=bundle, item=None, quantity=2, unit_price=Decimal("5")
        )

        StockManager.process_sale(sale)

        item1.refresh_from_db()
        item2.refresh_from_db()
        assert item1.quantity == 7
        assert item2.quantity == 8
