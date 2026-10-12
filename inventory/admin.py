from io import StringIO

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.management import call_command, CommandError
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path, reverse

from .models import (
    Bundle,
    BundleItem,
    Category,
    IngredientStock,
    Item,
    ItemIngredient,
    StockLog,
)
from users.models import Organization


class ItemIngredientInline(admin.TabularInline):
    model = ItemIngredient
    extra = 0
    raw_id_fields = ("ingredient",)


class BundleItemInline(admin.TabularInline):
    model = BundleItem
    extra = 0
    raw_id_fields = ("item",)


class FillSampleInventoryForm(forms.Form):
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.order_by("name"),
        help_text="Add the example categories, items, ingredients, and bundles to this organization.",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "fill-samples/",
                self.admin_site.admin_view(self.fill_samples_view),
                name="inventory_category_fill_samples",
            )
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_fill_samples"] = (
            request.user.is_superuser and settings.ROLE == "server"
        )
        return super().changelist_view(request, extra_context=extra_context)

    def fill_samples_view(self, request):
        if not request.user.is_superuser or settings.ROLE == "terminal":
            raise PermissionDenied

        if request.method == "POST":
            form = FillSampleInventoryForm(request.POST)
            if form.is_valid():
                output = StringIO()
                try:
                    call_command(
                        "fill_stock",
                        str(form.cleaned_data["organization"].pk),
                        stdout=output,
                    )
                except CommandError as error:
                    self.message_user(request, str(error), level=messages.ERROR)
                else:
                    self.message_user(
                        request,
                        output.getvalue().strip(),
                        level=messages.SUCCESS,
                    )
                    return redirect("admin:inventory_category_changelist")
        else:
            form = FillSampleInventoryForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
            "title": "Add dummy inventory",
        }
        return render(request, "admin/inventory/fill_samples.html", context)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'retail_price', 'wholesale_price', 'created_at')
    list_filter = ('category',)
    search_fields = ('name', 'sku')
    raw_id_fields = ('category',)
    inlines = (ItemIngredientInline,)


@admin.register(IngredientStock)
class IngredientStockAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "quantity",
        "wholesale_price",
        "retail_price",
        "added_as",
        "updated_at",
    )
    list_filter = ("organization", "added_as")
    search_fields = ("name",)
    raw_id_fields = ("organization",)
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(ItemIngredient)
class ItemIngredientAdmin(admin.ModelAdmin):
    list_display = ("item", "ingredient", "quantity")
    list_filter = ("item__organization",)
    search_fields = ("item__name", "ingredient__name")
    raw_id_fields = ("item", "ingredient")
    readonly_fields = ("uuid",)


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "price", "active", "updated_at")
    list_filter = ("organization", "active")
    search_fields = ("name",)
    raw_id_fields = ("organization",)
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = (BundleItemInline,)


@admin.register(BundleItem)
class BundleItemAdmin(admin.ModelAdmin):
    list_display = ("bundle", "item", "quantity")
    list_filter = ("bundle__organization",)
    search_fields = ("bundle__name", "item__name")
    raw_id_fields = ("bundle", "item")
    readonly_fields = ("uuid",)


@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "organization",
        "change_quantity",
        "reason",
        "performed_by",
        "created_at",
    )
    list_filter = ("organization", "reason", "created_at")
    search_fields = ("item__name", "performed_by__username", "note")
    raw_id_fields = ("item", "organization", "performed_by", "sale")
    readonly_fields = (
        "uuid",
        "organization",
        "item",
        "performed_by",
        "change_quantity",
        "reason",
        "revenue",
        "cost",
        "note",
        "created_at",
        "sale",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
