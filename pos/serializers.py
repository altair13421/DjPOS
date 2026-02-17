from decimal import Decimal
from rest_framework import serializers
from .models import Customer, Sale, CartItem
from inventory.models import Item, Bundle


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'created_at', 'updated_at']


class CartItemReadSerializer(serializers.ModelSerializer):
    """Read-only representation of a sale line (item or bundle)."""
    item = serializers.SerializerMethodField()
    bundle = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'item', 'bundle', 'quantity', 'unit_price', 'line_total']

    def get_line_total(self, obj):
        return obj.line_total

    def get_item(self, obj):
        if obj.item_id is None:
            return None
        return {'id': obj.item_id, 'name': obj.item.name}

    def get_bundle(self, obj):
        if obj.bundle_id is None:
            return None
        return {'id': obj.bundle_id, 'name': obj.bundle.name}


class SaleItemField(serializers.Field):
    """Accepts { item_id, quantity } or { bundle_id, quantity }."""

    def to_internal_value(self, data):
        item_id = data.get('item_id')
        bundle_id = data.get('bundle_id')
        quantity = data.get('quantity')
        if quantity is None or (not isinstance(quantity, int) and not isinstance(quantity, str)):
            raise serializers.ValidationError("quantity is required and must be a number.")
        quantity = int(quantity)
        if quantity < 1:
            raise serializers.ValidationError("quantity must be at least 1.")
        if item_id is not None and bundle_id is not None:
            raise serializers.ValidationError("Provide either item_id or bundle_id, not both.")
        if item_id is None and bundle_id is None:
            raise serializers.ValidationError("Provide item_id or bundle_id.")
        if item_id is not None:
            try:
                item = Item.objects.get(pk=item_id)
            except Item.DoesNotExist:
                raise serializers.ValidationError(f"Item {item_id} not found.")
            return {'type': 'item', 'item': item, 'quantity': quantity}
        try:
            bundle = Bundle.objects.get(pk=bundle_id)
        except Bundle.DoesNotExist:
            raise serializers.ValidationError(f"Bundle {bundle_id} not found.")
        if not bundle.active:
            raise serializers.ValidationError(f"Bundle {bundle_id} is not active.")
        return {'type': 'bundle', 'bundle': bundle, 'quantity': quantity}


class SaleSerializer(serializers.ModelSerializer):
    items = serializers.ListField(
        child=SaleItemField(),
        write_only=True,
    )
    sale_items = CartItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'customer', 'total', 'created_at', 'updated_at', 'items', 'sale_items']
        read_only_fields = ['total']

    def create(self, validated_data):
        items_data = validated_data.pop('items')

        sale = Sale.objects.create(**validated_data)
        total = Decimal('0')

        for entry in items_data:
            quantity = entry['quantity']
            if entry['type'] == 'item':
                item = entry['item']
                unit_price = item.retail_price
                CartItem.objects.create(
                    sale=sale,
                    item=item,
                    bundle=None,
                    quantity=quantity,
                    unit_price=unit_price,
                )
            else:
                bundle = entry['bundle']
                unit_price = bundle.price
                CartItem.objects.create(
                    sale=sale,
                    item=None,
                    bundle=bundle,
                    quantity=quantity,
                    unit_price=unit_price,
                )
            total += unit_price * quantity

        sale.total = total
        sale.save()
        return sale
