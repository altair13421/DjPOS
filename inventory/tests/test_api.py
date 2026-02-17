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

    def test_create_bundle_multiple_items(self, api_client, category):
        item1 = Item.objects.create(
            name="Item1", category=category, quantity=5,
            retail_price=10, wholesale_price=6, sku="I1"
        )
        item2 = Item.objects.create(
            name="Item2", category=category, quantity=5,
            retail_price=20, wholesale_price=12, sku="I2"
        )
        data = {
            'name': 'Multi Bundle',
            'price': '25.00',
            'item_ids': [
                {'item_id': item1.id, 'quantity': 1},
                {'item_id': item2.id, 'quantity': 2}
            ]
        }
        response = api_client.post('/inventory/api/bundles/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        bundle = Bundle.objects.get(name='Multi Bundle')
        assert bundle.bundleitem_set.count() == 2
        qty_map = {bi.item_id: bi.quantity for bi in bundle.bundleitem_set.all()}
        assert qty_map[item1.id] == 1
        assert qty_map[item2.id] == 2

    def test_list_bundles(self, api_client, item):
        bundle = Bundle.objects.create(name="Existing Bundle", price=10.00)
        BundleItem.objects.create(bundle=bundle, item=item, quantity=1)

        response = api_client.get('/inventory/api/bundles/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == "Existing Bundle"

    def test_retrieve_bundle_includes_computed_prices(self, api_client, item):
        item.retail_price = 15
        item.wholesale_price = 8
        item.save()
        bundle = Bundle.objects.create(name="Combo", price=20)
        BundleItem.objects.create(bundle=bundle, item=item, quantity=2)

        response = api_client.get(f'/inventory/api/bundles/{bundle.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "Combo"
        assert response.data['price'] == '20.00'
        assert 'total_wholesale' in response.data
        assert 'total_retail' in response.data
        assert float(response.data['total_wholesale']) == 16.0  # 8 * 2
        assert float(response.data['total_retail']) == 30.0    # 15 * 2
        assert len(response.data['items']) == 1
        assert response.data['items'][0]['quantity'] == 2
        assert response.data['items'][0]['item_name'] == item.name

    def test_update_bundle_items(self, api_client, item, category):
        item2 = Item.objects.create(
            name="Extra", category=category, quantity=1,
            retail_price=5, wholesale_price=3, sku="EX"
        )
        bundle = Bundle.objects.create(name="Original", price=10)
        BundleItem.objects.create(bundle=bundle, item=item, quantity=1)

        data = {
            'name': 'Original',
            'price': '12.00',
            'item_ids': [
                {'item_id': item.id, 'quantity': 2},
                {'item_id': item2.id, 'quantity': 1}
            ]
        }
        response = api_client.patch(
            f'/inventory/api/bundles/{bundle.id}/',
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        bundle.refresh_from_db()
        assert bundle.price == 12
        assert bundle.bundleitem_set.count() == 2
        qty_map = {bi.item_id: bi.quantity for bi in bundle.bundleitem_set.all()}
        assert qty_map[item.id] == 2
        assert qty_map[item2.id] == 1

    def test_delete_bundle_unused(self, api_client, item):
        bundle = Bundle.objects.create(name="To Delete", price=5)
        BundleItem.objects.create(bundle=bundle, item=item, quantity=1)

        response = api_client.delete(f'/inventory/api/bundles/{bundle.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Bundle.objects.filter(pk=bundle.id).exists()

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
