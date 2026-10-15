from decimal import Decimal

import pytest

from inventory.models import Item
from pos.models import CartItem, Sale
from users.models import Organization


@pytest.mark.django_db
def test_dashboard_page_renders_chart_and_transaction_sections(api_client):
    response = api_client.get("/pos/")

    assert response.status_code == 200
    assert b"Sales performance" in response.content
    assert b"Recent transactions" in response.content
    assert b"salesTrendChart" in response.content


@pytest.mark.django_db
def test_dashboard_overview_returns_scoped_daily_metrics_and_recent_sales(
    api_client, organization, user
):
    item = Item.objects.create(
        organization=organization,
        name="House Coffee",
        sku="HOUSE-COFFEE",
        retail_price=Decimal("7.00"),
        wholesale_price=Decimal("6.00"),
    )
    sale = Sale.objects.create(
        organization=organization,
        created_by=user,
        total=Decimal("14.00"),
    )
    CartItem.objects.create(
        sale=sale,
        item=item,
        quantity=2,
        unit_price=Decimal("7.00"),
    )

    other_organization = Organization.objects.create(
        name="Other Store", slug="other-store"
    )
    Sale.objects.create(organization=other_organization, total=Decimal("500.00"))

    response = api_client.get("/pos/api/analytics/overview/")

    assert response.status_code == 200
    assert response.data["today"]["revenue"] == "14.00"
    assert response.data["today"]["cost"] == "12.00"
    assert response.data["today"]["profit"] == "2.00"
    assert response.data["today"]["sales_count"] == 1
    assert response.data["today"]["average_sale"] == "14.00"
    assert len(response.data["daily"]) == 7
    assert response.data["top_items"] == [
        {
            "item_name": "House Coffee",
            "total_sold": "2",
            "revenue": "14.00",
        }
    ]
    assert response.data["recent_sales"][0]["id"] == sale.pk
    assert response.data["recent_sales"][0]["item_count"] == 2
