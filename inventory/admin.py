from django.contrib import admin

from .models import Category, Item, Bundle


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "identifier", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "identifier")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "organization",
        "category",
        "quantity",
        "reorder_level",
        "retail_price",
        "wholesale_price",
        "created_at",
    )
    list_filter = ("organization", "category")
    search_fields = ("name", "sku")
    raw_id_fields = ("category",)


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "price", "active", "created_at")
    list_filter = ("organization", "active")
    search_fields = ("name",)
