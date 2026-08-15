import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from inventory.models import Item, Bundle, BundleItem
from organizations.models import Organization, OrganizationMembership
from pos.models import Sale, CartItem, Customer
from utils.stock_manager import StockManager


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="POS Org", slug="pos-org")


@pytest.fixture
def owner(organization):
    user = User.objects.create_user(username="posuser", password="pass12345")
    OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=OrganizationMembership.Role.OWNER,
    )
    return user


@pytest.fixture
def api_client(owner):
    client = APIClient()
    client.force_authenticate(user=owner)
    return client


@pytest.fixture
def customer(organization):
    return Customer.objects.create(organization=organization, name="Test Customer")


@pytest.fixture
def item(organization):
    return Item.objects.create(
        organization=organization,
        name="Test Item",
        sku="TI",
        quantity=100,
        retail_price=Decimal("10"),
        wholesale_price=Decimal("6"),
    )


@pytest.fixture
def bundle(item, organization):
    other = Item.objects.create(
        organization=organization,
        name="Other Item",
        sku="OI",
        quantity=100,
        retail_price=Decimal("5"),
        wholesale_price=Decimal("3"),
    )
    b = Bundle.objects.create(
        organization=organization, name="Test Bundle", price=Decimal("12"), active=True
    )
    BundleItem.objects.create(bundle=b, item=item, quantity=1)
    BundleItem.objects.create(bundle=b, item=other, quantity=1)
    return b


@pytest.mark.django_db
class TestSaleWithBundle:
    def test_create_sale_with_bundle_id(self, api_client, customer, bundle, organization):
        payload = {
            "customer": customer.id,
            "items": [{"bundle_id": bundle.id, "quantity": 2}],
        }
        response = api_client.post("/pos/api/sales/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Sale.objects.count() == 1
        sale = Sale.objects.first()
        assert sale.organization_id == organization.id
        assert sale.total == Decimal("24")
        ci = sale.sale_items.get(bundle_id=bundle.id)
        assert ci.item_id is None
        assert ci.unit_price == bundle.price
        assert ci.quantity == 2
        assert ci.line_total == Decimal("24")

    def test_create_sale_mixed_item_and_bundle(self, api_client, item, bundle):
        payload = {
            "customer": None,
            "items": [
                {"item_id": item.id, "quantity": 1},
                {"bundle_id": bundle.id, "quantity": 1},
            ],
        }
        response = api_client.post("/pos/api/sales/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        sale = Sale.objects.first()
        assert sale.total == Decimal("22")
        assert sale.sale_items.count() == 2

    def test_sale_read_includes_bundle_and_unit_price(self, api_client, bundle, organization):
        sale = Sale.objects.create(organization=organization, total=Decimal("12"))
        CartItem.objects.create(
            sale=sale,
            bundle=bundle,
            item=None,
            quantity=1,
            unit_price=Decimal("12"),
        )
        response = api_client.get("/pos/api/sales/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["results"][0]
        assert "sale_items" in data
        assert len(data["sale_items"]) == 1
        line = data["sale_items"][0]
        assert line["bundle"] == {"id": bundle.id, "name": bundle.name}
        assert line["item"] is None
        assert line["quantity"] == 1
        assert line["unit_price"] == "12.00"
        assert Decimal(line["line_total"]) == Decimal("12.00")

    def test_create_sale_invalid_bundle_id(self, api_client):
        payload = {"customer": None, "items": [{"bundle_id": 99999, "quantity": 1}]}
        response = api_client.post("/pos/api/sales/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_sale_inactive_bundle_rejected(self, api_client, bundle):
        bundle.active = False
        bundle.save()
        payload = {"customer": None, "items": [{"bundle_id": bundle.id, "quantity": 1}]}
        response = api_client.post("/pos/api/sales/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestBundleDeleteWhenUsedInSale:
    def test_delete_bundle_used_in_sale_fails(self, api_client, bundle, organization):
        from django.db.models.deletion import ProtectedError

        sale = Sale.objects.create(organization=organization, total=Decimal("12"))
        CartItem.objects.create(
            sale=sale,
            bundle=bundle,
            item=None,
            quantity=1,
            unit_price=Decimal("12"),
        )
        with pytest.raises(ProtectedError):
            api_client.delete(f"/inventory/api/bundles/{bundle.id}/")
        assert Bundle.objects.filter(pk=bundle.id).exists()


@pytest.mark.django_db
class TestProfitWithBundle:
    def test_profit_includes_bundle_cost(self, api_client, bundle, organization):
        sale = Sale.objects.create(organization=organization, total=Decimal("12"))
        CartItem.objects.create(
            sale=sale,
            bundle=bundle,
            item=None,
            quantity=1,
            unit_price=Decimal("12"),
        )
        StockManager.process_sale(sale)

        response = api_client.get("/pos/api/analytics/profit/")
        assert response.status_code == status.HTTP_200_OK
        assert float(response.data["revenue"]) == 12
        assert float(response.data["cost"]) == 9
        assert float(response.data["profit"]) == 3
