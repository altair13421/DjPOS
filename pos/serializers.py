from rest_framework import serializers
from .models import Customer, Sale


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'created_at', 'updated_at']


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ['id', 'customer', 'total', 'created_at', 'updated_at']
