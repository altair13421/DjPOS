from django.contrib import admin

from .models import Customer, Sale


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "email", "phone", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "email", "phone")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "customer", "total", "created_at")
    list_filter = ("organization", "created_at")
    raw_id_fields = ("customer",)
