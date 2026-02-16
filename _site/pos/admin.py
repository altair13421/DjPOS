from django.contrib import admin
from .models import Customer, Sale


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'phone')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total', 'created_at')
    list_filter = ('created_at',)
    raw_id_fields = ('customer',)
