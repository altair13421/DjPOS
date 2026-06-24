from collections import defaultdict
from decimal import Decimal
from datetime import timedelta

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone

from pos.models import Sale
from inventory.models import Item


def _expanded_qty_rev_cost_for_sales(sales_qs):
    qty_by_item_id = defaultdict(Decimal)
    rev_by_item_id = defaultdict(Decimal)
    cost_by_item_id = defaultdict(Decimal)

    for sale in sales_qs:
        for cart_item in sale.sale_items.all():
            if cart_item.item_id:
                item = cart_item.item
                qty = Decimal(cart_item.quantity or 0)
                qty_by_item_id[item.id] += qty
                rev_by_item_id[item.id] += Decimal(cart_item.unit_price or 0) * qty
                cost_by_item_id[item.id] += Decimal(item.wholesale_price or 0) * qty

            elif cart_item.bundle_id:
                bundle = cart_item.bundle
                cart_qty = Decimal(cart_item.quantity or 0)
                bundle_revenue = Decimal(cart_item.unit_price or 0) * cart_qty

                components = list(bundle.bundleitem_set.all())

                total_bundle_wholesale = Decimal("0.00")
                for bi in components:
                    total_bundle_wholesale += Decimal(bi.quantity or 0) * Decimal(bi.item.wholesale_price or 0)

                for bi in components:
                    component_qty_in_one_bundle = Decimal(bi.quantity or 0)
                    component_qty_sold = component_qty_in_one_bundle * cart_qty

                    component_wholesale_value = component_qty_in_one_bundle * Decimal(
                        bi.item.wholesale_price or 0
                    )

                    share = (component_wholesale_value / total_bundle_wholesale) if total_bundle_wholesale > 0 else Decimal("0.00")

                    qty_by_item_id[bi.item_id] += component_qty_sold
                    rev_by_item_id[bi.item_id] += bundle_revenue * share
                    cost_by_item_id[bi.item_id] += component_wholesale_value * cart_qty

    return qty_by_item_id, rev_by_item_id, cost_by_item_id


class AnalyticsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def profit(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        sales = (
            Sale.objects.filter(created_at__gte=today_start, created_at__lt=tomorrow_start)
            .prefetch_related(
                "sale_items__item",
                "sale_items__bundle__bundleitem_set__item",
            )
        )

        revenue_total = sales.aggregate(total=Sum("total"))["total"] or Decimal("0.00")

        qty_by_item_id, rev_by_item_id, cost_by_item_id = _expanded_qty_rev_cost_for_sales(sales)

        total_cost = sum(cost_by_item_id.values(), Decimal("0.00"))
        profit_total = revenue_total - total_cost

        items_breakdown = [
            {
                "item_id": item_id,
                "total_sold": str(qty_by_item_id[item_id]),
                "revenue": str(rev_by_item_id[item_id]),
                "cost": str(cost_by_item_id[item_id]),
                "profit": str(rev_by_item_id[item_id] - cost_by_item_id[item_id]),
            }
            for item_id in qty_by_item_id.keys()
        ]
        items_breakdown.sort(key=lambda x: Decimal(x["total_sold"]), reverse=True)

        return Response({
            "revenue": str(revenue_total),
            "cost": str(total_cost),
            "profit": str(profit_total),
            "items": items_breakdown,
        })

    def _last_7d_sales(self):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        return Sale.objects.filter(created_at__range=[start_date, end_date]).prefetch_related(
            "sale_items__item",
            "sale_items__bundle__bundleitem_set__item",
        )

    @action(detail=False, methods=["get"])
    def items_sold_7d(self, request):
        sales = self._last_7d_sales()
        qty_by_item_id, _, _ = _expanded_qty_rev_cost_for_sales(sales)

        item_ids = list(qty_by_item_id.keys())
        names = dict(Item.objects.filter(id__in=item_ids).values_list("id", "name"))

        result = [
            {"item_name": names.get(iid, str(iid)), "total_sold": qty}
            for iid, qty in qty_by_item_id.items()
        ]
        result.sort(key=lambda x: x["total_sold"], reverse=True)
        return Response(result[:20])

    @action(detail=False, methods=["get"])
    def top_items(self, request):
        sales = self._last_7d_sales()
        qty_by_item_id, _, _ = _expanded_qty_rev_cost_for_sales(sales)

        item_ids = list(qty_by_item_id.keys())
        names = dict(Item.objects.filter(id__in=item_ids).values_list("id", "name"))

        result = [
            {"item_name": names.get(iid, str(iid)), "total_sold": qty}
            for iid, qty in qty_by_item_id.items()
        ]
        result.sort(key=lambda x: x["total_sold"], reverse=True)
        return Response(result[:5])

