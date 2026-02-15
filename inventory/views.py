from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
)
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Category, Item, Bundle, StockLog
from .serializers import CategorySerializer, ItemSerializer, BundleSerializer, StockLogSerializer
from .forms import CategoryForm, ItemForm


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


# ——— API (DRF) ———

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related("category").all()
    serializer_class = ItemSerializer


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
