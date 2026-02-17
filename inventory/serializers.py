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
    retail_price = serializers.DecimalField(
        source='item.retail_price', max_digits=12, decimal_places=2, read_only=True
    )
    wholesale_price = serializers.DecimalField(
        source='item.wholesale_price', max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = BundleItem
        fields = ['id', 'item', 'item_name', 'quantity', 'retail_price', 'wholesale_price']


class BundleSerializer(serializers.ModelSerializer):
    items = BundleItemSerializer(source='bundleitem_set', many=True, read_only=True)
    total_wholesale = serializers.SerializerMethodField()
    total_retail = serializers.SerializerMethodField()

    def get_total_wholesale(self, obj):
        return obj.total_wholesale

    def get_total_retail(self, obj):
        return obj.total_retail
    item_ids = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Bundle
        fields = [
            'id', 'name', 'price', 'active', 'items',
            'total_wholesale', 'total_retail', 'item_ids',
            'created_at', 'updated_at'
        ]

    def _item_ids_internal_value(self, item_ids):
        out = []
        for d in item_ids or []:
            item_id = d.get('item_id')
            quantity = d.get('quantity', 1)
            if item_id is None:
                continue
            out.append({'item_id': int(item_id), 'quantity': int(quantity)})
        return out

    def create(self, validated_data):
        item_ids = self._item_ids_internal_value(validated_data.pop('item_ids', []))
        bundle = Bundle.objects.create(**validated_data)
        for item_data in item_ids:
            BundleItem.objects.create(
                bundle=bundle,
                item_id=item_data['item_id'],
                quantity=item_data['quantity']
            )
        return bundle

    def update(self, instance, validated_data):
        item_ids = validated_data.pop('item_ids', None)
        instance.name = validated_data.get('name', instance.name)
        instance.price = validated_data.get('price', instance.price)
        instance.active = validated_data.get('active', instance.active)
        instance.save()
        if item_ids is not None:
            instance.bundleitem_set.all().delete()
            for item_data in self._item_ids_internal_value(item_ids):
                BundleItem.objects.create(
                    bundle=instance,
                    item_id=item_data['item_id'],
                    quantity=item_data['quantity']
                )
        return instance


class StockLogSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)

    class Meta:
        model = StockLog
        fields = ['id', 'item', 'item_name', 'change_quantity', 'reason', 'reason_display', 'note', 'created_at']
