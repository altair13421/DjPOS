import json
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Category, Item, Bundle, BundleItem, StockLog
from .serializers import CategorySerializer, ItemSerializer, BundleSerializer, StockLogSerializer
from .forms import CategoryForm, ItemForm, BundleForm
from rest_framework.decorators import action
from utils.stock_manager import StockManager
from .choices import StockChangeReason


class IndexView(TemplateView):
    """Inventory app dashboard."""
    template_name = "inventory/index.html"


# ——— Category UI ———

class CategoryListView(ListView):
    model = Category
    queryset = Category.objects.all().order_by("name")
    context_object_name = "categories"
    template_name = "inventory/category_list.html"


class CategoryCreateView(SuccessMessageMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = "Category created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class CategoryUpdateView(SuccessMessageMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    context_object_name = "category"
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = "Category updated."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context


# ——— Item UI (add category on same page) ———

class ItemListView(ListView):
    model = Item
    queryset = Item.objects.select_related("category").all().order_by("-created_at")
    context_object_name = "items"
    template_name = "inventory/item_list.html"


class ItemCreateView(SuccessMessageMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")
    success_message = "Item created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class ItemUpdateView(SuccessMessageMixin, UpdateView):
    model = Item
    form_class = ItemForm
    context_object_name = "item"
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")
    success_message = "Item updated."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context


# ——— Bundle UI ———

class BundleListView(ListView):
    model = Bundle
    queryset = Bundle.objects.prefetch_related("bundleitem_set").order_by("-created_at")
    context_object_name = "bundles"
    template_name = "inventory/bundle_list.html"


class BundleCreateView(SuccessMessageMixin, CreateView):
    model = Bundle
    form_class = BundleForm
    template_name = "inventory/bundle_form.html"
    success_url = reverse_lazy("inventory:bundle_list")
    success_message = "Bundle created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        items = Item.objects.all().order_by("name")
        context["items_json"] = json.dumps([
            {"id": i.id, "name": i.name, "retail_price": str(i.retail_price), "wholesale_price": str(i.wholesale_price)}
            for i in items
        ])
        context["bundle_items_json"] = "[]"
        return context

    def form_valid(self, form):
        items_json = self.request.POST.get("items_json", "[]")
        try:
            item_ids = json.loads(items_json)
        except (json.JSONDecodeError, TypeError):
            item_ids = []
        with transaction.atomic():
            bundle = form.save()
            BundleItem.objects.filter(bundle=bundle).delete()
            for entry in item_ids:
                if isinstance(entry, dict) and "item_id" in entry:
                    BundleItem.objects.create(
                        bundle=bundle,
                        item_id=int(entry["item_id"]),
                        quantity=int(entry.get("quantity", 1)),
                    )
        return super().form_valid(form)


class BundleUpdateView(SuccessMessageMixin, UpdateView):
    model = Bundle
    form_class = BundleForm
    context_object_name = "bundle"
    template_name = "inventory/bundle_form.html"
    success_url = reverse_lazy("inventory:bundle_list")
    success_message = "Bundle updated."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        items = Item.objects.all().order_by("name")
        context["items_json"] = json.dumps([
            {"id": i.id, "name": i.name, "retail_price": str(i.retail_price), "wholesale_price": str(i.wholesale_price)}
            for i in items
        ])
        bundle_items = list(
            self.object.bundleitem_set.select_related("item").values(
                "item_id", "quantity"
            )
        ) if self.object.pk else []
        context["bundle_items_json"] = json.dumps(bundle_items)
        return context

    def form_valid(self, form):
        items_json = self.request.POST.get("items_json", "[]")
        try:
            item_ids = json.loads(items_json)
        except (json.JSONDecodeError, TypeError):
            item_ids = []
        with transaction.atomic():
            bundle = form.save()
            BundleItem.objects.filter(bundle=bundle).delete()
            for entry in item_ids:
                if isinstance(entry, dict) and "item_id" in entry:
                    BundleItem.objects.create(
                        bundle=bundle,
                        item_id=int(entry["item_id"]),
                        quantity=int(entry.get("quantity", 1)),
                    )
        return super().form_valid(form)


class BundleDeleteView(DeleteView):
    model = Bundle
    context_object_name = "bundle"
    template_name = "inventory/bundle_confirm_delete.html"
    success_url = reverse_lazy("inventory:bundle_list")

    def delete(self, request, *args, **kwargs):
        from django.db.models.deletion import ProtectedError
        from django.shortcuts import redirect
        try:
            return super().delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                "Cannot delete this bundle because it has been used in at least one sale.",
            )
            return redirect("inventory:bundle_list")


class InventoryStatsView(TemplateView):
    """Overall inventory stats view."""
    template_name = "inventory/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        items = list(Item.objects.annotate(
            total_sold_raw=Coalesce(
                Sum('stock_logs__change_quantity', filter=Q(stock_logs__reason=StockChangeReason.SALE)),
                0
            ),
            total_restocked=Coalesce(
                Sum('stock_logs__change_quantity', filter=Q(stock_logs__reason=StockChangeReason.RESTOCK)),
                0
            )
        ).select_related('category').order_by('name'))
        
        for item in items:
            item.total_sold = -item.total_sold_raw if item.total_sold_raw else 0

        context['items'] = items
        return context


# ——— API (DRF) ———

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related("category").all()
    serializer_class = ItemSerializer

    @action(detail=True, methods=['post'])
    def restock(self, request, pk=None):
        item = self.get_object()
        quantity = int(request.data.get('quantity', 0))
        reason = request.data.get('reason', StockChangeReason.RESTOCK)
        note = request.data.get('note', '')
        
        StockManager.restock_item(item, quantity, reason, note)
        return Response({'status': 'restocked', 'new_quantity': item.quantity})


class BundleViewSet(viewsets.ModelViewSet):
    queryset = Bundle.objects.prefetch_related("items").all().order_by("-created_at")
    serializer_class = BundleSerializer


class StockLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for stock logs.
    """
    queryset = StockLog.objects.select_related("item").all().order_by("-created_at")
    serializer_class = StockLogSerializer
    filterset_fields = ['item', 'reason']


class ApiRootView(APIView):
    def get(self, request):
        return Response({
            "categories": request.build_absolute_uri("categories/"),
            "items": request.build_absolute_uri("items/"),
            "bundles": request.build_absolute_uri("bundles/"),
            "stock_logs": request.build_absolute_uri("stock_logs/"),
        })
