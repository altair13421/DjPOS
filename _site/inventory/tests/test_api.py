import pytest
from rest_framework import status
from rest_framework.test import APIClient
from inventory.models import Category, Item, Bundle, BundleItem

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def category():
    return Category.objects.create(name="Test Category")

@pytest.fixture
def item(category):
    return Item.objects.create(
        name="Test Item",
        category=category,
        sku="TEST-001",
        quantity=10,
        cost_price=5.00,
        retail_price=10.00
    )

@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories(self, api_client, category):
        response = api_client.get('/inventory/api/categories/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == category.name

    def test_create_category(self, api_client):
        data = {'name': 'New Category', 'description': 'Description'}
        response = api_client.post('/inventory/api/categories/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Category.objects.count() == 1

@pytest.mark.django_db
class TestItemAPI:
    def test_list_items(self, api_client, item):
        response = api_client.get('/inventory/api/items/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == item.name

    def test_create_item(self, api_client, category):
        data = {
            'name': 'New Item',
            'sku': 'NEW-001',
            'category': category.id,
            'quantity': 5,
            'retail_price': '20.00'
        }
        response = api_client.post('/inventory/api/items/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Item.objects.count() == 1

@pytest.mark.django_db
class TestBundleAPI:
    def test_create_bundle(self, api_client, item):
        data = {
            'name': 'Test Bundle',
            'price': '15.00',
            'item_ids': [{'item_id': item.id, 'quantity': 1}]
        }
        response = api_client.post('/inventory/api/bundles/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Bundle.objects.count() == 1
        assert Bundle.objects.first().items.count() == 1

    def test_list_bundles(self, api_client, item):
        bundle = Bundle.objects.create(name="Existing Bundle", price=10.00)
        BundleItem.objects.create(bundle=bundle, item=item, quantity=1)
        
        response = api_client.get('/inventory/api/bundles/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == "Existing Bundle"

@pytest.mark.django_db
class TestStockLogAPI:
    def test_list_stock_logs(self, api_client, item):
        # Initial log from item creation via StockManager or similar (if hooks existed, but here we just check access)
        # We manually create a log for testing read access
        from inventory.models import StockLog
        StockLog.objects.create(item=item, change_quantity=5, reason="RESTOCK")
        
        response = api_client.get('/inventory/api/stock_logs/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['item_name'] == item.name
