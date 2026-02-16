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
