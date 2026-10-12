from decimal import Decimal
from types import SimpleNamespace

import pytest

from inventory.models import Item
from pos.models import Sale
from pos.serializers import SaleSerializer


@pytest.mark.django_db
def test_sale_discount_is_a_percentage_of_the_whole_sale(organization, user):
    item = Item.objects.create(
        organization=organization,
        name="Coffee",
        sku="COFFEE",
        retail_price=Decimal("15.35"),
    )
    serializer = SaleSerializer(
        data={
            "customer": {
                "name": "Walk-in",
                "email": "",
                "phone": "",
                "address": "",
                "type_cus": "WALK_IN",
            },
            "items": [{"item_id": item.pk, "quantity": 2}],
            "discount_percent": "10",
        },
        context={"request": SimpleNamespace(organization=organization)},
    )

    assert serializer.is_valid(), serializer.errors
    sale = serializer.save(organization=organization, created_by=user)

    assert sale.total == Decimal("30.70")
    assert sale.discount == Decimal("3.07")


@pytest.mark.django_db
@pytest.mark.parametrize("discount_percent", ["-0.01", "100.01", "abc"])
def test_sale_rejects_invalid_discount_percent(organization, discount_percent):
    serializer = SaleSerializer(
        data={
            "customer": {
                "name": "Walk-in",
                "email": "",
                "phone": "",
                "address": "",
                "type_cus": "WALK_IN",
            },
            "items": [],
            "discount_percent": discount_percent,
        },
        context={"request": SimpleNamespace(organization=organization)},
    )

    assert not serializer.is_valid()
    assert "discount_percent" in serializer.errors
