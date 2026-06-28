from icecream import ic
import json
from django.contrib import messages
from users.api_mixins import OrganizationViewSetMixin
from users.mixins import OrgLoginRequiredMixin, OrganizationScopedMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.db.models import (
    Sum, F, Q, Value, DecimalField, ExpressionWrapper, OuterRef, Subquery
)
from decimal import Decimal
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

from .models import Category, Item, Bundle, BundleItem, StockLog, IngredientStock, ItemIngredient
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    BundleSerializer,
    StockLogSerializer,
    IngredientStockSerializer,
    ItemIngredientSerializer

)
from .forms import CategoryForm, ItemForm, BundleForm, IngredientStockForm
from rest_framework.decorators import action
from utils.stock_manager import StockManager
from .choices import StockChangeReason, StockAddedAs


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)   # or str(o) to preserve exact representation
        return super().default(o)

class IndexView(OrgLoginRequiredMixin, TemplateView):
    """Inventory app dashboard."""
    template_name = "inventory/index.html"


# ——— Category UI ———

class CategoryListView(OrgLoginRequiredMixin, OrganizationScopedMixin, ListView):
    model = Category
    queryset = Category.objects.all().order_by("name")
    context_object_name = "categories"
    template_name = "inventory/category_list.html"


class CategoryCreateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventory/category_form.html"
    success_url = reverse_lazy("inventory:category_list")
    success_message = "Category created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class CategoryUpdateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, UpdateView):
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


# ---- IngredientStock UI ----

class StockListView(OrgLoginRequiredMixin, OrganizationScopedMixin, ListView):
    model = IngredientStock
    queryset = IngredientStock.objects.all()
    context_object_name = "stock"
    template_name = 'inventory/stock_list.html'

class StockCreateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, CreateView):
    model = IngredientStock
    form_class = IngredientStockForm
    template_name = 'inventory/stock_form.html'
    success_url = reverse_lazy("inventory:stock_list")
    success_message = "Stock Created"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(organization=self.request.organization)
        context["is_edit"] = False
        return context

    def form_valid(self, form):
        stock = self.request.POST
        is_item = stock.get('is_item', "off")
        org = self.request.organization
        with transaction.atomic():
            ingredient = form.save(commit=False)
            ingredient.organization = org
            ingredient.save()
            if is_item == "on":
                ingredient.added_as = StockAddedAs.ITEM
                new_category_name: str = stock.get("new_category_name", "")
                category_existing: int = int(stock.get("category", "0"))

                category: Category | None = None
                if category_existing != 0 and new_category_name != "":
                    ingredient.delete()
                    return super().form_invalid(form)
                if category_existing != 0:
                    category = Category.objects.get(id=category_existing, organization=org)
                elif new_category_name != "":
                    category, _ = Category.objects.get_or_create(
                        name=new_category_name, organization=org
                    )

                if not category:
                    category, _ = Category.objects.get_or_create(
                        name="ItemFromStock", organization=org
                    )
                item = Item.objects.create(
                    name=ingredient.name,
                    sku=stock.get("sku", ""),
                    category=category,
                    organization=org,
                    retail_price=ingredient.retail_price,
                    wholesale_price=ingredient.wholesale_price,
                )
                ingredient.item_id = item.id
                ingredient.save()
                ItemIngredient.objects.get_or_create(
                    item=item,
                    ingredient=ingredient,
                    defaults={"quantity": stock.get("quantity_consumed", 1)},
                )

        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class StockUpdateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, UpdateView):
    model = IngredientStock
    form_class = IngredientStockForm
    template_name = 'inventory/stock_form.html'
    success_url = reverse_lazy("inventory:stock_list")
    success_message = "Stock Updated."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        context['ingredient'] = self.get_object()
        if context['ingredient'].added_as == StockAddedAs.ITEM:
            context['categories'] = Category.objects.filter(organization=self.request.organization)
            context['item'] = Item.objects.get(
                id=context['ingredient'].item_id, organization=self.request.organization
            )
            item_ingredient = ItemIngredient.objects.filter(
                item=context["item"],
                ingredient=context["ingredient"],
            ).first()
            context["quantity_consumed"] = item_ingredient.quantity
        return context

    def form_valid(self, form):
        stock = self.request.POST
        is_item = stock.get('is_item', "off")
        with transaction.atomic():
            ingredient = form.save()
            if is_item == "on":
                ingredient.added_as = StockAddedAs.ITEM
                category_existing: int = int(stock.get("category", "0")) # is category id

                category: Category | None = Category.objects.none
                if category_existing != 0:
                    category = Category.objects.get(id=category_existing)
                
                item = Item.objects.get(id=stock.get("item_id"))
                item.wholesale_price = ingredient.wholesale_price
                item.retail_price = ingredient.retail_price
                item.sku = stock.get("sku", item.sku)
                item.save()
                itemIng, _ = ItemIngredient.objects.get_or_create(
                    item=item,
                    ingredient=ingredient,
                )
                itemIng.quantity=stock.get("quantity_consumed", 1)
                itemIng.save()
        return super().form_valid(form)




# ——— Item UI (add category on same page) ———

class ItemListView(OrgLoginRequiredMixin, OrganizationScopedMixin, ListView):
    model = Item
    queryset = Item.objects.select_related("category").all().order_by("-created_at")
    context_object_name = "items"
    template_name = "inventory/item_list.html"


class ItemCreateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")
    success_message = "Item created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        ingredients = IngredientStock.objects.filter(
            organization=self.request.organization
        ).order_by("name")
        context["ingredients_json"] = json.dumps([
            {"id": ing.id, "name": ing.name, "retail_price": str(ing.retail_price), "wholesale_price": str(ing.wholesale_price)}
            for ing in ingredients
        ])
        context["items_json"] = '[]'
        return context

    def form_valid(self, form):
        ingredients_json = self.request.POST.get("ingredients_json", "[]")
        try:
            ingredient_ids = json.loads(ingredients_json)
        except (json.JSONDecodeError, TypeError):
            ingredients_ids = []
        with transaction.atomic():
            item = form.save()
            ItemIngredient.objects.filter(item=item).delete()
            for entry in ingredient_ids:
                if isinstance(entry, dict) and "ingredient_id" in entry:
                    ItemIngredient.objects.create(
                        item=item,
                        ingredient_id=int(entry["ingredient_id"]),
                        quantity=Decimal(entry.get("quantity", 1)),
                    )

        return super().form_valid(form)

class ItemUpdateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, UpdateView):
    model = Item
    form_class = ItemForm
    context_object_name = "item"
    template_name = "inventory/item_form.html"
    success_url = reverse_lazy("inventory:item_list")
    success_message = "Item updated."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        ingredients = IngredientStock.objects.filter(
            organization=self.request.organization
        ).order_by("name")
        context["ingredients_json"] = json.dumps([
            {"id": ing.id, "name": ing.name, "retail_price": str(ing.retail_price), "wholesale_price": str(ing.wholesale_price)}
            for ing in ingredients
        ])
        item_ingredients = list(
            self.object.itemingredient_set.select_related("ingredient").values(
                "ingredient_id", "quantity"
            )
        ) if self.object.pk else []
        context["items_json"] = json.dumps(item_ingredients, cls=DecimalEncoder)
        return context

    def form_valid(self, form):
        ingredients_json = self.request.POST.get("ingredients_json", "[]")
        try:
            ingredient_ids = json.loads(ingredients_json)
        except (json.JSONDecodeError, TypeError):
            ingredients_ids = []
        with transaction.atomic():
            item = form.save()
            ItemIngredient.objects.filter(item=item).delete()
            for entry in ingredient_ids:
                if isinstance(entry, dict) and "ingredient_id" in entry:
                    ItemIngredient.objects.create(
                        item=item,
                        ingredient_id=int(entry["ingredient_id"]),
                        quantity=Decimal(entry.get("quantity", 1)),
                    )

        return super().form_valid(form)


# ——— Bundle UI ———

class BundleListView(OrgLoginRequiredMixin, OrganizationScopedMixin, ListView):
    model = Bundle
    queryset = Bundle.objects.prefetch_related("bundleitem_set").order_by("-created_at")
    context_object_name = "bundles"
    template_name = "inventory/bundle_list.html"


class BundleCreateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, CreateView):
    model = Bundle
    form_class = BundleForm
    template_name = "inventory/bundle_form.html"
    success_url = reverse_lazy("inventory:bundle_list")
    success_message = "Bundle created."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        items = Item.objects.filter(organization=self.request.organization).order_by("name")
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


class BundleUpdateView(OrgLoginRequiredMixin, OrganizationScopedMixin, SuccessMessageMixin, UpdateView):
    model = Bundle
    form_class = BundleForm
    context_object_name = "bundle"
    template_name = "inventory/bundle_form.html"
    success_url = reverse_lazy("inventory:bundle_list")
    success_message = "Bundle updated."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        items = Item.objects.filter(organization=self.request.organization).order_by("name")
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


class BundleDeleteView(OrgLoginRequiredMixin, OrganizationScopedMixin, DeleteView):
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

'''
class InventoryStatsView(TemplateView):
    """Overall inventory stats view."""
    template_name = "inventory/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        items = list(IngredientStock.objects.annotate(
            total_sold_raw=Coalesce(
                Sum('stock_logs__change_quantity', filter=Q(stock_logs__reason=StockChangeReason.SALE)),
                0
            ),
            total_restocked=Coalesce(
                Sum('stock_logs__change_quantity', filter=Q(stock_logs__reason=StockChangeReason.RESTOCK)),
                0
            ),
            total_revenue=Coalesce(
                Sum('stock_logs__revenue', filter=Q(stock_logs__reason=StockChangeReason.SALE)),
                Decimal('0.00')
            ),
            total_cost=Coalesce(
                Sum('stock_logs__cost', filter=Q(stock_logs__reason=StockChangeReason.SALE)),
                Decimal('0.00')
            ) # We only consider the cost at the time of sale.
        ).order_by('name'))
        
        for item in items:
            item.total_sold = -item.total_sold_raw if item.total_sold_raw else 0
            item.profit = item.total_revenue - item.total_cost

        context['items'] = items
        return context
'''

class InventoryStatsView(OrgLoginRequiredMixin, TemplateView):
    template_name = "inventory/stats.html"

    def get_context_data(self, **kwargs):
        from pos.models import CartItem

        context = super().get_context_data(**kwargs)
        org = self.request.organization
        item_qs = Item.objects.filter(organization=org)
        cart_base = CartItem.objects.filter(sale__organization=org)

        # -------------------------
        # 1) Sold quantity per Item
        # -------------------------
        direct_qty_sub = (
            cart_base.filter(item=OuterRef("pk"), bundle__isnull=True)
            .values("item")
            .annotate(qty=Coalesce(Sum("quantity", output_field=DecimalField()), Value(0, output_field=DecimalField())))
            .values("qty")[:1]
        )

        # bundle-expanded qty: sum(bundleitem.quantity * cart_item.quantity)
        bundle_qty_sub = (
            cart_base.filter(bundle__isnull=False)
            .filter(bundle__bundleitem__item=OuterRef("pk"))
            .values("bundle__bundleitem__item")
            .annotate(
                qty=Coalesce(
                    Sum(F("bundle__bundleitem__quantity") * F("quantity"), output_field=DecimalField()),
                    Value(0, output_field=DecimalField()),
                )
            )
            .values("qty")[:1]
        )

        total_qty = Coalesce(Subquery(direct_qty_sub, output_field=DecimalField()), Value(0, output_field=DecimalField())) + \
                 Coalesce(Subquery(bundle_qty_sub, output_field=DecimalField()), Value(0, output_field=DecimalField()))

        # --------------------------------
        # 2) Cost per Item (expanded similarly)
        # --------------------------------
        direct_cost_sub = (
            cart_base.filter(item=OuterRef("pk"), bundle__isnull=True)
            .values("item")
            .annotate(
                cost=Coalesce(
                    Sum(F("item__wholesale_price") * F("quantity"), output_field=DecimalField()),
                    Value(0, output_field=DecimalField()),
                )
            )
            .values("cost")[:1]
        )

        bundle_cost_sub = (
            cart_base.filter(bundle__isnull=False)
            .filter(bundle__bundleitem__item=OuterRef("pk"))
            .values("bundle__bundleitem__item")
            .annotate(
                cost=Coalesce(
                    Sum(
                        F("bundle__bundleitem__quantity")
                        * F("bundle__bundleitem__item__wholesale_price")
                        * F("quantity"),
                        output_field=DecimalField()
                    ),
                    Value(0, output_field=DecimalField()),
                )
            )
            .values("cost")[:1]
        )

        total_cost = Coalesce(Subquery(direct_cost_sub, output_field=DecimalField()), Value(0, output_field=DecimalField())) + \
                  Coalesce(Subquery(bundle_cost_sub, output_field=DecimalField()), Value(0, output_field=DecimalField()))

        # ---------------------------------------------------
        # 3) Revenue per Item
        #   - direct: unit_price * quantity
        #   - bundle: allocate cart_item.unit_price across underlying items
        #            by wholesale_value share within the bundle line
        # ---------------------------------------------------
        direct_rev_sub = (
            cart_base.filter(item=OuterRef("pk"), bundle__isnull=True)
            .values("item")
            .annotate(
                rev=Coalesce(
                    Sum(F("unit_price") * F("quantity")),
                    Value(0),
                )
            )
            .values("rev")[:1]
        )

        # For bundle allocation, we need:
        # underlying_wholesale_value_for_this_item_on_this_cartline
        # -----------------------------------------------------------
        # numerator: (bundleitem.quantity * item.wholesale_price) * cart_item.quantity
        #
        # denominator: total wholesale value of the whole bundle line:
        #   sum_over_bundleitems( bundleitem.quantity * item.wholesale_price ) * cart_item.quantity
        #
        # cart_item.quantity cancels out, so allocation fraction is independent of cart_item.quantity,
        # but we still compute per underlying item for each cart line.
        bundle_rev_sub = (
            cart_base.filter(bundle__isnull=False)
            .filter(bundle__bundleitem__item=OuterRef("pk"))
            .values("bundle__bundleitem__item")
            .annotate(
                # numerator
                numer=Coalesce(
                    Sum(
                        (F("bundle__bundleitem__quantity") * F("bundle__bundleitem__item__wholesale_price"))
                    ),
                    Value(0),
                ),
                # denominator (sum of wholesale values for the whole bundle)
                denom=Coalesce(
                    Sum(
                        F("bundle__bundleitem__quantity")
                        * F("bundle__bundleitem__item__wholesale_price")
                    ),
                    Value(0),
                ),
            )
            # The above doesn't isolate denom correctly per cart line; we need a different approach.
            # Simpler/accurate allocation requires per cart line aggregation.
        )

        # Because Django ORM subquery allocation across "each cart line" is messy without extra models,
        # here’s the reliable approach:
        # - compute direct item revenue directly
        # - compute bundle revenue revenue_allocation in Python with prefetch.
        # We’ll do that below using one query to fetch relevant cart lines.

        qs = item_qs.order_by("name").values("id", "name", "wholesale_price")
        items = {row["id"]: {"id": row["id"], "name": row["name"]} for row in qs}

        # Seed qty & cost via DB expressions
        seeded = (
            item_qs.annotate(
                total_sold_qty=total_qty,
                total_cost=total_cost,
            )
            .values("id", "total_sold_qty", "total_cost", "name")
            .order_by("name")
        )

        items_list = []
        for r in seeded:
            item_id = r["id"]
            items[item_id]["total_sold_qty"] = r["total_sold_qty"] or 0
            items[item_id]["total_cost"] = r["total_cost"] or 0

        # Bundle revenue allocation in Python (exact per cart line)
        bundle_lines = cart_base.filter(bundle__isnull=False).select_related("bundle").prefetch_related(
            "bundle__bundleitem_set"
        )

        direct_lines = cart_base.filter(bundle__isnull=True, item__isnull=False).select_related("item")

        for ci in direct_lines:
            item_id = ci.item_id
            items[item_id]["total_revenue"] = items[item_id].get("total_revenue", 0) + (ci.unit_price * ci.quantity)

        for ci in bundle_lines:
            # total wholesale value of the bundle contents for THIS cart line
            bundle_wholesale_total = sum(
                (bi.quantity * bi.item.wholesale_price)
                for bi in ci.bundle.bundleitem_set.all()
            ) or 0

            # cart row revenue is the bundle deal price times the cart line quantity
            bundle_revenue = ci.unit_price * ci.quantity

            for bi in ci.bundle.bundleitem_set.all():
                underlying = bi.item
                item_id = underlying.id

                if bundle_wholesale_total:
                    share = (bi.quantity * underlying.wholesale_price) / bundle_wholesale_total
                else:
                    share = 0

                items[item_id]["total_revenue"] = items[item_id].get("total_revenue", 0) + (bundle_revenue * share)

        # Finalize profit
        for it in items.values():
            total_revenue = it.get("total_revenue", 0) or 0
            total_cost = it.get("total_cost", 0) or 0
            it["profit"] = total_revenue - total_cost
            items_list.append(it)

        context["items"] = sorted(items_list, key=lambda x: x["name"])
        ic(context['items'])
        return context


# ——— API (DRF) ———

class IngredientStockViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = IngredientStock.objects.all()
    serializer_class = IngredientStockSerializer

    @action(detail=True, methods=['post'])
    def restock(self, request, pk=None):
        stock_item = self.get_object()
        quantity = int(request.data.get('quantity', 0))
        reason = request.data.get('reason', StockChangeReason.RESTOCK)
        note = request.data.get('note', 'note')

        StockManager.restock_item(
            stock_item, quantity, reason, note, performed_by=request.user
        )
        return Response({'status': 'restocked', 'new_quantity': stock_item.quantity})

class CategoryViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ItemViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = Item.objects.select_related("category").all()
    serializer_class = ItemSerializer

class BundleViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = Bundle.objects.prefetch_related("items").all().order_by("-created_at")
    serializer_class = BundleSerializer


class StockLogViewSet(OrganizationViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for stock logs.
    """
    queryset = StockLog.objects.select_related("item").all().order_by("-created_at")
    serializer_class = StockLogSerializer
    filterset_fields = ['item', 'reason']


class ApiRootView(APIView):
    def get(self, request):
        if not getattr(request, "organization", None):
            return Response({"detail": "Organization required."}, status=403)
        return Response({
            "categories": request.build_absolute_uri("categories/"),
            "items": request.build_absolute_uri("items/"),
            "bundles": request.build_absolute_uri("bundles/"),
            "stock_logs": request.build_absolute_uri("stock_logs/"),
            "ingredients": request.build_absolute_uri("inventory/"),
        })
