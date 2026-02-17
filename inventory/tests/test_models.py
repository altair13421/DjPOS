import pytest
from decimal import Decimal
from inventory.models import Item, Bundle, BundleItem


@pytest.mark.django_db
def test_bundle_creation():
    item1 = Item.objects.create(name="Burger", quantity=10, cost_price=2, sku="BURGER")
    item2 = Item.objects.create(name="Fries", quantity=10, cost_price=1, sku="FRIES")

    bundle = Bundle.objects.create(name="Meal Deal", price=5)

    BundleItem.objects.create(bundle=bundle, item=item1, quantity=1)
    BundleItem.objects.create(bundle=bundle, item=item2, quantity=1)

    assert bundle.items.count() == 2
    assert bundle.items.first().name in ["Burger", "Fries"]


@pytest.mark.django_db
class TestBundleModel:
    def test_bundle_total_wholesale_and_retail(self):
        item1 = Item.objects.create(
            name="A", quantity=10, retail_price=Decimal("10"), wholesale_price=Decimal("5"), sku="A"
        )
        item2 = Item.objects.create(
            name="B", quantity=10, retail_price=Decimal("20"), wholesale_price=Decimal("12"), sku="B"
        )
        bundle = Bundle.objects.create(name="Combo", price=Decimal("25"))
        BundleItem.objects.create(bundle=bundle, item=item1, quantity=1)
        BundleItem.objects.create(bundle=bundle, item=item2, quantity=2)

        assert bundle.total_wholesale == Decimal("5") + Decimal("12") * 2  # 29
        assert bundle.total_retail == Decimal("10") + Decimal("20") * 2  # 50

    def test_bundle_str(self):
        bundle = Bundle.objects.create(name="Meal Deal", price=Decimal("9.99"))
        assert "Meal Deal" in str(bundle)
        assert "9.99" in str(bundle)

    def test_bundle_item_str(self):
        item = Item.objects.create(name="Soda", quantity=5, sku="SODA")
        bundle = Bundle.objects.create(name="Lunch", price=Decimal("5"))
        bi = BundleItem.objects.create(bundle=bundle, item=item, quantity=2)
        assert "2" in str(bi)
        assert "Soda" in str(bi)
        assert "Lunch" in str(bi)

    def test_bundle_empty_totals(self):
        bundle = Bundle.objects.create(name="Empty Bundle", price=Decimal("0"))
        assert bundle.total_wholesale == 0
        assert bundle.total_retail == 0
