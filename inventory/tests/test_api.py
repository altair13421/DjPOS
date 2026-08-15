from math import ceil
from decimal import Decimal

import pytest
from django.contrib.auth.models import User

from organizations.models import Organization, OrganizationMembership
from inventory.models import Category, Item, Bundle, BundleItem


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Test Org", slug="test-org")


@pytest.fixture
def owner(organization):
    user = User.objects.create_user(username="tester", password="pass12345")
    OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role=OrganizationMembership.Role.OWNER,
    )
    return user


@pytest.fixture
def api_client(owner):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=owner)
    return client


@pytest.fixture
def category(organization):
    return Category.objects.create(
        organization=organization, name="Test Category", identifier="TEST"
    )


@pytest.fixture
def item(organization, category):
    return Item.objects.create(
        organization=organization,
        name="Test Item",
        category=category,
        sku="TEST-001",
        quantity=10,
        cost_price=5.00,
        retail_price=10.00,
    )


@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories(self, api_client, category):
        response = api_client.get("/inventory/api/categories/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == category.name

    def test_create_category(self, api_client, organization):
        data = {"name": "New Category", "description": "Description"}
        response = api_client.post("/inventory/api/categories/", data)
        assert response.status_code == 201
        assert Category.objects.filter(organization=organization).count() == 1


@pytest.mark.django_db
class TestItemAPI:
    def test_list_items(self, api_client, item):
        response = api_client.get("/inventory/api/items/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == item.name

    def test_create_item(self, api_client, category, organization):
        data = {
            "name": "New Item",
            "sku": "NEW-001",
            "category": category.id,
            "quantity": 5,
            "retail_price": "20.00",
        }
        response = api_client.post("/inventory/api/items/", data)
        assert response.status_code == 201
        created = Item.objects.get(sku="NEW-001")
        assert created.organization_id == organization.id
        assert created.quantity == 5


@pytest.mark.django_db
class TestBundleAPI:
    def test_create_bundle(self, api_client, item):
        data = {
            "name": "Test Bundle",
            "price": "15.00",
            "item_ids": [{"item_id": item.id, "quantity": 1}],
        }
        response = api_client.post("/inventory/api/bundles/", data, format="json")
        assert response.status_code == 201
        assert Bundle.objects.count() == 1
        assert Bundle.objects.first().bundleitem_set.count() == 1

    def test_create_bundle_multiple_items(self, api_client, category, organization):
        item1 = Item.objects.create(
            organization=organization,
            name="Item1",
            category=category,
            quantity=5,
            retail_price=10,
            wholesale_price=6,
            sku="I1",
        )
        item2 = Item.objects.create(
            organization=organization,
            name="Item2",
            category=category,
            quantity=5,
            retail_price=20,
            wholesale_price=12,
            sku="I2",
        )
        data = {
            "name": "Multi Bundle",
            "price": "25.00",
            "item_ids": [
                {"item_id": item1.id, "quantity": 1},
                {"item_id": item2.id, "quantity": 2},
            ],
        }
        response = api_client.post("/inventory/api/bundles/", data, format="json")
        assert response.status_code == 201
        bundle = Bundle.objects.get(name="Multi Bundle")
        assert bundle.bundleitem_set.count() == 2
        qty_map = {bi.item_id: bi.quantity for bi in bundle.bundleitem_set.all()}
        assert qty_map[item1.id] == 1
        assert qty_map[item2.id] == 2

    def test_list_bundles(self, api_client, item, organization):
        bundle = Bundle.objects.create(
            organization=organization, name="Existing Bundle", price=10.00
        )
        BundleItem.objects.create(bundle=bundle, item=item, quantity=1)

        response = api_client.get("/inventory/api/bundles/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Existing Bundle"

    def test_retrieve_bundle_includes_computed_prices(self, api_client, item, organization):
        item.retail_price = 15
        item.wholesale_price = 8
        item.save()
        bundle = Bundle.objects.create(
            organization=organization, name="Combo", price=20
        )
        BundleItem.objects.create(bundle=bundle, item=item, quantity=2)

        response = api_client.get(f"/inventory/api/bundles/{bundle.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "Combo"
        assert response.data["price"] == "20.00"
        assert float(response.data["total_wholesale"]) == 16.0
        assert float(response.data["total_retail"]) == 30.0
        assert len(response.data["items"]) == 1
        assert response.data["items"][0]["quantity"] == 2
        assert response.data["items"][0]["item_name"] == item.name

    def test_update_bundle_items(self, api_client, item, category, organization):
        item2 = Item.objects.create(
            organization=organization,
            name="Extra",
            category=category,
            quantity=1,
            retail_price=5,
            wholesale_price=3,
            sku="EX",
        )
        bundle = Bundle.objects.create(
            organization=organization, name="Original", price=10
        )
        BundleItem.objects.create(bundle=bundle, item=item, quantity=1)

        data = {
            "name": "Original",
            "price": "12.00",
            "item_ids": [
                {"item_id": item.id, "quantity": 2},
                {"item_id": item2.id, "quantity": 1},
            ],
        }
        response = api_client.patch(
            f"/inventory/api/bundles/{bundle.id}/",
            data,
            format="json",
        )
        assert response.status_code == 200
        bundle.refresh_from_db()
        assert bundle.price == 12
        assert bundle.bundleitem_set.count() == 2


@pytest.mark.django_db
def test_quantity_ceiling_round_helper():
    assert int(ceil(Decimal("1.1"))) == 2
    assert int(ceil(Decimal("2.0"))) == 2
    assert int(ceil(Decimal("0.1"))) == 1
