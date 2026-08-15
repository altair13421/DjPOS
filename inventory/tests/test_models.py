import pytest
from decimal import Decimal
from inventory.models import Item, Bundle, BundleItem
from organizations.models import Organization


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Model Org", slug="model-org")


@pytest.mark.django_db
def test_bundle_creation(organization):
    item1 = Item.objects.create(
        organization=organization, name="Burger", quantity=10, cost_price=2, sku="BURGER"
    )
    item2 = Item.objects.create(
        organization=organization, name="Fries", quantity=10, cost_price=1, sku="FRIES"
    )

    bundle = Bundle.objects.create(
        organization=organization, name="Meal Deal", price=5
    )

    BundleItem.objects.create(bundle=bundle, item=item1, quantity=1)
    BundleItem.objects.create(bundle=bundle, item=item2, quantity=1)

    assert bundle.bundleitem_set.count() == 2
    names = {bi.item.name for bi in bundle.bundleitem_set.all()}
    assert names == {"Burger", "Fries"}


@pytest.mark.django_db
class TestBundleModel:
    def test_bundle_total_wholesale_and_retail(self, organization):
        item1 = Item.objects.create(
            organization=organization,
            name="A",
            quantity=10,
            retail_price=Decimal("10"),
            wholesale_price=Decimal("5"),
            sku="A",
        )
        item2 = Item.objects.create(
            organization=organization,
            name="B",
            quantity=10,
            retail_price=Decimal("20"),
            wholesale_price=Decimal("12"),
            sku="B",
        )
        bundle = Bundle.objects.create(
            organization=organization, name="Combo", price=Decimal("25")
        )
        BundleItem.objects.create(bundle=bundle, item=item1, quantity=1)
        BundleItem.objects.create(bundle=bundle, item=item2, quantity=2)

        assert bundle.total_wholesale == Decimal("5") + Decimal("12") * 2
        assert bundle.total_retail == Decimal("10") + Decimal("20") * 2

    def test_bundle_str(self, organization):
        bundle = Bundle.objects.create(
            organization=organization, name="Meal Deal", price=Decimal("9.99")
        )
        assert "Meal Deal" in str(bundle)
        assert "9.99" in str(bundle)

    def test_bundle_item_str(self, organization):
        item = Item.objects.create(
            organization=organization, name="Soda", quantity=5, sku="SODA"
        )
        bundle = Bundle.objects.create(
            organization=organization, name="Lunch", price=Decimal("5")
        )
        bi = BundleItem.objects.create(bundle=bundle, item=item, quantity=2)
        assert "2" in str(bi)
        assert "Soda" in str(bi)
        assert "Lunch" in str(bi)

    def test_bundle_empty_totals(self, organization):
        bundle = Bundle.objects.create(
            organization=organization, name="Empty Bundle", price=Decimal("0")
        )
        assert bundle.total_wholesale == 0
        assert bundle.total_retail == 0

    def test_item_is_low_stock(self, organization):
        item = Item.objects.create(
            organization=organization,
            name="Cheese",
            sku="CH",
            quantity=3,
            reorder_level=5,
        )
        assert item.is_low_stock is True
        item.quantity = 6
        assert item.is_low_stock is False
