import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.mixins import (
    OrganizationFormMixin,
    OrganizationQuerysetMixin,
    OrganizationRequiredMixin,
    OrganizationViewSetMixin,
    IsOrganizationMember,
)
from organizations.utils import get_user_organization
from utils.stock_manager import StockManager

from .choices import StockChangeReason
from .forms import CategoryForm, ItemForm, BundleForm
from .models import Category, Item, Bundle, BundleItem, StockLog
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    BundleSerializer,
    StockLogSerializer,
)
from pos.models import Sale


def dec_to_native(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class IndexView(OrganizationRequiredMixin, TemplateView):
    """Inventory app dashboard with stock alerts."""

    template_name = "inventory/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        items = list(
            Item.objects.filter(organization=organization).select_related("category")
        )
        low_stock_all = [item for item in items if item.quantity <= item.reorder_level]
        low_stock_items = sorted(
            low_stock_all, key=lambda item: (item.quantity, item.name)
        )[:20]

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_sales = Sale.objects.filter(
            organization=organization, created_at__gte=today_start
        )
        today_revenue = today_sales.aggregate(total=Sum("total"))["total"] or Decimal("0")

        context.update(
            {
                "total_items": len(items),
                "out_of_stock_count": sum(1 for item in items if item.quantity == 0),
                "low_stock_count": len(low_stock_all),
                "today_sales_count": today_sales.count(),
                "today_revenue": today_revenue,
                "low_stock_items": low_stock_items,
            }
        )
        return context


# ——— Category UI ———


class CategoryListView(OrganizationQuerysetMixin, ListView):
    model = Category
    queryset = Category.objects.all().order_by("name")
    context_object_name = "categories"
    template_name = "inventory/category_list.html"


class CategoryCreateView(OrganizationFormMixin, SuccessMessageMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = "Category created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class CategoryUpdateView(OrganizationFormMixin, SuccessMessageMixin, UpdateView):
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


# ——— Item UI ———


class ItemListView(OrganizationQuerysetMixin, ListView):
    model = Item
    queryset = Item.objects.select_related("category").all().order_by("-created_at")
    context_object_name = "items"
    template_name = "inventory/item_list.html"


class ItemCreateView(OrganizationFormMixin, SuccessMessageMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")
    success_message = "Item created."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.get_organization()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class ItemUpdateView(OrganizationFormMixin, SuccessMessageMixin, UpdateView):
    model = Item
    form_class = ItemForm
    context_object_name = "item"
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")
    success_message = "Item updated."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.get_organization()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context


# ——— Bundle UI ———


class BundleListView(OrganizationQuerysetMixin, ListView):
    model = Bundle
    queryset = Bundle.objects.prefetch_related("bundleitem_set").order_by("-created_at")
    context_object_name = "bundles"
    template_name = "inventory/bundle_list.html"


class BundleCreateView(OrganizationFormMixin, SuccessMessageMixin, CreateView):
    model = Bundle
    form_class = BundleForm
    template_name = "inventory/bundle_form.html"
    success_url = reverse_lazy("inventory:bundle_list")
    success_message = "Bundle created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        organization = self.get_organization()
        items = Item.objects.filter(organization=organization).order_by("name")
        bundles = Bundle.objects.filter(organization=organization).order_by("name")
        bundles_json = [
            {
                "id": b.id,
                "name": b.name,
                "retail_price": str(b.total_retail),
                "wholesale_price": str(b.total_wholesale),
                "bundle": True,
            }
            for b in bundles
        ]
        items_json = [
            {
                "id": i.id,
                "name": i.name,
                "retail_price": str(i.retail_price),
                "wholesale_price": str(i.wholesale_price),
            }
            for i in items
        ]
        context["items_json"] = json.dumps(items_json + bundles_json)
        context["bundle_items_json"] = "[]"
        return context

    def form_valid(self, form):
        items_json = self.request.POST.get("items_json", "[]")
        try:
            item_ids = json.loads(items_json)
        except (json.JSONDecodeError, TypeError):
            item_ids = []
        organization = self.get_organization()
        with transaction.atomic():
            form.instance.organization = organization
            self.object = form.save()
            BundleItem.objects.filter(bundle=self.object).delete()
            for entry in item_ids:
                if not (isinstance(entry, dict) and "item_id" in entry):
                    continue
                kind, raw_id = entry["item_id"].split("-", 1)
                quantity = int(entry.get("quantity", 1))
                if kind == "bundle":
                    nested = Bundle.objects.get(pk=int(raw_id), organization=organization)
                    BundleItem.objects.create(
                        bundle=self.object,
                        bundle_included=nested,
                        quantity=quantity,
                    )
                else:
                    item = Item.objects.get(pk=int(raw_id), organization=organization)
                    BundleItem.objects.create(
                        bundle=self.object,
                        item=item,
                        quantity=quantity,
                    )
        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class BundleUpdateView(OrganizationFormMixin, SuccessMessageMixin, UpdateView):
    model = Bundle
    form_class = BundleForm
    context_object_name = "bundle"
    template_name = "inventory/bundle_form.html"
    success_url = reverse_lazy("inventory:bundle_list")
    success_message = "Bundle updated."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        organization = self.get_organization()
        items = Item.objects.filter(organization=organization).order_by("name")
        bundles = Bundle.objects.filter(organization=organization).order_by("name")
        bundles_json = [
            {
                "id": b.id,
                "name": b.name,
                "retail_price": str(b.total_retail),
                "wholesale_price": str(b.total_wholesale),
                "bundle": True,
            }
            for b in bundles
            if b.id != self.object.id
        ]
        items_json = [
            {
                "id": i.id,
                "name": i.name,
                "retail_price": str(i.retail_price),
                "wholesale_price": str(i.wholesale_price),
                "bundle": False,
            }
            for i in items
        ]
        context["items_json"] = json.dumps(
            (items_json + bundles_json), default=dec_to_native
        )
        bundle_items = (
            list(
                self.object.bundleitem_set.select_related("item", "bundle_included").values(
                    "item_id", "quantity", "bundle_included_id"
                )
            )
            if self.object.pk
            else []
        )
        context["bundle_items_json"] = json.dumps(bundle_items, default=dec_to_native)
        return context

    def form_valid(self, form):
        items_json = self.request.POST.get("items_json", "[]")
        try:
            item_ids = json.loads(items_json)
        except (json.JSONDecodeError, TypeError):
            item_ids = []
        organization = self.get_organization()
        with transaction.atomic():
            self.object = form.save()
            BundleItem.objects.filter(bundle=self.object).delete()
            for entry in item_ids:
                if not (isinstance(entry, dict) and "item_id" in entry):
                    continue
                kind, raw_id = entry["item_id"].split("-", 1)
                quantity = int(entry.get("quantity", 1))
                if kind == "bundle":
                    nested = Bundle.objects.get(pk=int(raw_id), organization=organization)
                    BundleItem.objects.create(
                        bundle=self.object,
                        bundle_included=nested,
                        quantity=quantity,
                    )
                else:
                    item = Item.objects.get(pk=int(raw_id), organization=organization)
                    BundleItem.objects.create(
                        bundle=self.object,
                        item=item,
                        quantity=quantity,
                    )
        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class BundleDeleteView(OrganizationQuerysetMixin, DeleteView):
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


class InventoryStatsView(OrganizationRequiredMixin, TemplateView):
    """Overall inventory stats view."""

    template_name = "inventory/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()

        items = list(
            Item.objects.filter(organization=organization)
            .annotate(
                total_sold_raw=Coalesce(
                    Sum(
                        "stock_logs__change_quantity",
                        filter=Q(stock_logs__reason=StockChangeReason.SALE),
                    ),
                    0,
                ),
                total_restocked=Coalesce(
                    Sum(
                        "stock_logs__change_quantity",
                        filter=Q(stock_logs__reason=StockChangeReason.RESTOCK),
                    ),
                    0,
                ),
                total_revenue=Coalesce(
                    Sum(
                        "stock_logs__revenue",
                        filter=Q(stock_logs__reason=StockChangeReason.SALE),
                    ),
                    Decimal("0.00"),
                ),
                total_cost=Coalesce(
                    Sum(
                        "stock_logs__cost",
                        filter=Q(stock_logs__reason=StockChangeReason.SALE),
                    ),
                    Decimal("0.00"),
                ),
            )
            .select_related("category")
            .order_by("name")
        )

        for item in items:
            item.total_sold = -item.total_sold_raw if item.total_sold_raw else 0
            item.profit = item.total_revenue - item.total_cost

        context["items"] = items
        return context


# ——— API (DRF) ———


class CategoryViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ItemViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = Item.objects.select_related("category").all()
    serializer_class = ItemSerializer

    @action(detail=True, methods=["post"])
    def restock(self, request, pk=None):
        item = self.get_object()
        quantity = int(request.data.get("quantity", 0))
        reason = request.data.get("reason", StockChangeReason.RESTOCK)
        note = request.data.get("note", "")
        StockManager.restock_item(item, quantity, reason, note)
        return Response({"status": "restocked", "new_quantity": item.quantity})


class BundleViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = Bundle.objects.prefetch_related("items").all().order_by("-created_at")
    serializer_class = BundleSerializer


class StockLogViewSet(OrganizationViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockLog.objects.select_related("item").all().order_by("-created_at")
    serializer_class = StockLogSerializer
    filterset_fields = ["item", "reason"]
    organization_field = "item__organization"


class ApiRootView(APIView):
    permission_classes = [IsOrganizationMember]

    def get(self, request):
        return Response(
            {
                "categories": request.build_absolute_uri("categories/"),
                "items": request.build_absolute_uri("items/"),
                "bundles": request.build_absolute_uri("bundles/"),
                "stock_logs": request.build_absolute_uri("stock_logs/"),
            }
        )
