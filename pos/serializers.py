from rest_framework import serializers
from .models import Customer, Sale, CartItem
from inventory.models import Item


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'created_at', 'updated_at']


class SaleSerializer(serializers.ModelSerializer):
    items = serializers.ListField(write_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'customer', 'total', 'created_at', 'updated_at', 'items']
        read_only_fields = ['total']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Create Sale
        sale = Sale.objects.create(**validated_data)
        
        # Create Sale Items
        total = 0
        for item_data in items_data:
            item = Item.objects.get(id=item_data['item_id'])
            quantity = item_data['quantity']
            price = item.retail_price * quantity
            total += price
            
            CartItem.objects.create(
                sale=sale,
                item=item,
                quantity=quantity
            )
        
        sale.total = total
        sale.save()
        return sale
