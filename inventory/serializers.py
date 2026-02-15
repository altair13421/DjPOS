from rest_framework import serializers
from .models import Category, Item, Bundle, BundleItem, StockLog


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'sku', 'category', 'quantity',
            'retail_price', 'wholesale_price', 'created_at', 'updated_at',
        ]


class BundleItemSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')

    class Meta:
        model = BundleItem
        fields = ['id', 'item', 'item_name', 'quantity']


class BundleSerializer(serializers.ModelSerializer):
    items = BundleItemSerializer(source='bundleitem_set', many=True, read_only=True)
    item_ids = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        write_only=True,
        required=False
    )

    class Meta:
        model = Bundle
        fields = ['id', 'name', 'price', 'active', 'items', 'item_ids', 'created_at', 'updated_at']

    def create(self, validated_data):
        item_ids = validated_data.pop('item_ids', [])
        bundle = Bundle.objects.create(**validated_data)
        
        for item_data in item_ids:
            BundleItem.objects.create(
                bundle=bundle,
                item_id=item_data['item_id'],
                quantity=item_data.get('quantity', 1)
            )
        return bundle


class StockLogSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)

    class Meta:
        model = StockLog
        fields = ['id', 'item', 'item_name', 'change_quantity', 'reason', 'reason_display', 'note', 'created_at']
