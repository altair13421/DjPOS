from decimal import Decimal

import pytest

from inventory.models import Item
from pos.models import CartItem, Sale


@pytest.mark.django_db
def test_inventory_stats_displays_summary_and_revenue_chart(
    api_client, organization, user
):
    item = Item.objects.create(
        organization=organization,
        name="Tea",
        sku="TEA-1",
        retail_price=Decimal("10.00"),
        wholesale_price=Decimal("6.00"),
    )
    sale = Sale.objects.create(
        organization=organization,
        created_by=user,
        total=Decimal("20.00"),
    )
    CartItem.objects.create(
        sale=sale,
        item=item,
        quantity=2,
        unit_price=Decimal("10.00"),
    )

    response = api_client.get("/inventory/stats/")

    assert response.status_code == 200
    assert b"Top items by revenue" in response.content
    assert b"inventoryRevenueChart" in response.content
    assert b"Tea" in response.content
    assert b"12.00" in response.content
