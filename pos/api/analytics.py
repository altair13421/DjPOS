from collections import defaultdict
from decimal import Decimal
from datetime import datetime, time, timedelta

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
    def _org_sales(self, request):
        org = getattr(request, "organization", None)
        if org is None:
            return Sale.objects.none()
        return Sale.objects.filter(organization=org)

    @action(detail=False, methods=["get"])
    def profit(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        sales = (
            self._org_sales(request)
            .filter(created_at__gte=today_start, created_at__lt=tomorrow_start)
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

    def _last_7d_sales(self, request):
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        return self._org_sales(request).filter(created_at__range=[start_date, end_date]).prefetch_related(
            "sale_items__item",
            "sale_items__bundle__bundleitem_set__item",
        )

    @action(detail=False, methods=["get"])
    def overview(self, request):
        organization = getattr(request, "organization", None)
        if organization is None:
            return Response({"detail": "Organization required."}, status=403)

        today = timezone.localdate()
        first_day = today - timedelta(days=6)
        current_tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(first_day, time.min), current_tz)
        end = timezone.make_aware(
            datetime.combine(today + timedelta(days=1), time.min), current_tz
        )
        sales = list(
            self._org_sales(request)
            .filter(created_at__gte=start, created_at__lt=end)
            .select_related("customer")
            .prefetch_related(
                "sale_items__item",
                "sale_items__bundle__bundleitem_set__item",
            )
            .order_by("-created_at")
        )

        sales_by_day = defaultdict(list)
        for sale in sales:
            sales_by_day[timezone.localdate(sale.created_at)].append(sale)

        daily = []
        week_item_qty = defaultdict(Decimal)
        week_item_revenue = defaultdict(Decimal)
        today_revenue = Decimal("0.00")
        today_cost = Decimal("0.00")
        today_count = 0
        for day_offset in range(7):
            day = first_day + timedelta(days=day_offset)
            day_sales = sales_by_day[day]
            revenue = sum((sale.total for sale in day_sales), Decimal("0.00"))
            quantities, item_revenues, item_costs = _expanded_qty_rev_cost_for_sales(
                day_sales
            )
            cost = sum(item_costs.values(), Decimal("0.00"))
            daily.append(
                {
                    "date": day.isoformat(),
                    "revenue": str(revenue),
                    "cost": str(cost),
                    "profit": str(revenue - cost),
                    "sales_count": len(day_sales),
                }
            )
            for item_id, quantity in quantities.items():
                week_item_qty[item_id] += quantity
                week_item_revenue[item_id] += item_revenues[item_id]
            if day == today:
                today_revenue = revenue
                today_cost = cost
                today_count = len(day_sales)

        item_ids = list(week_item_qty)
        names = dict(
            Item.objects.filter(
                id__in=item_ids, organization=organization
            ).values_list("id", "name")
        )
        top_items = [
            {
                "item_name": names.get(item_id, str(item_id)),
                "total_sold": str(quantity),
                "revenue": str(week_item_revenue[item_id]),
            }
            for item_id, quantity in week_item_qty.items()
        ]
        top_items.sort(
            key=lambda item: Decimal(item["total_sold"]), reverse=True
        )
        top_items = top_items[:5]

        return Response(
            {
                "today": {
                    "revenue": str(today_revenue),
                    "cost": str(today_cost),
                    "profit": str(today_revenue - today_cost),
                    "sales_count": today_count,
                    "average_sale": str(
                        today_revenue / today_count if today_count else Decimal("0.00")
                    ),
                },
                "daily": daily,
                "top_items": top_items,
                "recent_sales": [
                    {
                        "id": sale.pk,
                        "customer": sale.customer.name if sale.customer else "Walk-in",
                        "created_at": sale.created_at.isoformat(),
                        "total": str(sale.total),
                        "item_count": sum(
                            line.quantity for line in sale.sale_items.all()
                        ),
                    }
                    for sale in sales[:6]
                ],
            }
        )

    @action(detail=False, methods=["get"])
    def items_sold_7d(self, request):
        sales = self._last_7d_sales(request)
        qty_by_item_id, _, _ = _expanded_qty_rev_cost_for_sales(sales)

        item_ids = list(qty_by_item_id.keys())
        names = dict(
            Item.objects.filter(id__in=item_ids, organization=request.organization).values_list("id", "name")
        )

        result = [
            {"item_name": names.get(iid, str(iid)), "total_sold": qty}
            for iid, qty in qty_by_item_id.items()
        ]
        result.sort(key=lambda x: x["total_sold"], reverse=True)
        return Response(result[:20])

    @action(detail=False, methods=["get"])
    def top_items(self, request):
        sales = self._last_7d_sales(request)
        qty_by_item_id, _, _ = _expanded_qty_rev_cost_for_sales(sales)

        item_ids = list(qty_by_item_id.keys())
        names = dict(
            Item.objects.filter(id__in=item_ids, organization=request.organization).values_list("id", "name")
        )

        result = [
            {"item_name": names.get(iid, str(iid)), "total_sold": qty}
            for iid, qty in qty_by_item_id.items()
        ]
        result.sort(key=lambda x: x["total_sold"], reverse=True)
        return Response(result[:5])
