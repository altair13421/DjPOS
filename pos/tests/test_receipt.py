from decimal import Decimal

import pytest

from inventory.models import Bundle, BundleItem, Item
from pos.models import CartItem, Sale


@pytest.mark.django_db
def test_receipt_page_renders_sale_details_and_thermal_print_layout(
    api_client, user, organization
):
    item = Item.objects.create(
        organization=organization,
        name="Coffee",
        sku="COFFEE",
        retail_price=Decimal("5.00"),
    )
    bundle_item = Item.objects.create(
        organization=organization,
        name="Cookie",
        sku="COOKIE",
        retail_price=Decimal("2.00"),
    )
    bundle = Bundle.objects.create(
        organization=organization,
        name="Coffee combo",
        price=Decimal("6.00"),
    )
    BundleItem.objects.create(bundle=bundle, item=bundle_item, quantity=1)
    sale = Sale.objects.create(
        organization=organization,
        created_by=user,
        total=Decimal("11.00"),
        discount=Decimal("1.10"),
        paid=Decimal("12.00"),
        change=Decimal("1.00"),
    )
    CartItem.objects.create(
        sale=sale,
        item=item,
        quantity=1,
        unit_price=Decimal("5.00"),
    )
    CartItem.objects.create(
        sale=sale,
        bundle=bundle,
        quantity=1,
        unit_price=Decimal("6.00"),
    )

    response = api_client.get(f"/pos/sale/{sale.pk}/receipt/")

    assert response.status_code == 200
    assert b"Coffee combo (Bundle)" in response.content
    assert b"Cookie x 1" in response.content
    assert b"Cashier: testuser" in response.content
    assert b"Tax (18%)" in response.content
    assert b"Discount (10%)" in response.content
    assert b"TOTAL" in response.content
    assert b"Paid" in response.content
    assert b"size: 80mm auto" in response.content
    assert b"window.print()" in response.content


@pytest.mark.django_db
def test_sale_panel_shows_tax_rate_and_discount_percentage(api_client):
    response = api_client.get("/pos/sale_panel/")

    assert response.status_code == 200
    assert b"Tax rate:" in response.content
    assert b"18%" in response.content
    assert b"Discount (0%)" in response.content
