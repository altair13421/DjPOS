from django.contrib import admin
from .models import Category, Item


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'quantity', 'unit_price', 'created_at')
    list_filter = ('category',)
    search_fields = ('name', 'sku')
    raw_id_fields = ('category',)
