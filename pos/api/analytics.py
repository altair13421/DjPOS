from collections import defaultdict
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from pos.models import Sale, CartItem
from inventory.models import Item


def _item_quantities_sold(start_date, end_date, limit=None):
    """
    Return list of { item_name, total_sold } for the date range.
    Counts standalone item sales and expands bundle sales into component items.
    Sorted by total_sold descending. If limit set, return top N.
    """
    sales = Sale.objects.filter(
        created_at__range=[start_date, end_date]
    ).prefetch_related(
        'sale_items__item',
        'sale_items__bundle__bundleitem_set__item',
    )
    by_name = defaultdict(int)
    for sale in sales:
        for cart_item in sale.sale_items.all():
            if cart_item.item_id:
                by_name[cart_item.item.name] += cart_item.quantity
            elif cart_item.bundle_id:
                for bi in cart_item.bundle.bundleitem_set.all():
                    by_name[bi.item.name] += bi.quantity * cart_item.quantity
    result = [
        {"item_name": name, "total_sold": total}
        for name, total in sorted(by_name.items(), key=lambda x: -x[1])
    ]
    if limit:
        result = result[:limit]
    return result


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for POS analytics and reporting.
    """

    @action(detail=False, methods=['get'])
    def daily_sales(self, request):
        """Total sales for the last 7 days."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        sales = Sale.objects.filter(
            created_at__range=[start_date, end_date]
        ).values('created_at__date').annotate(
            total=Sum('total')
        ).order_by('created_at__date')
        return Response(sales)

    @action(detail=False, methods=['get'])
    def top_items(self, request):
        """Top 5 selling items in the last 7 days (includes items from bundles)."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        result = _item_quantities_sold(start_date, end_date, limit=5)
        return Response(result)

    @action(detail=False, methods=['get'])
    def items_sold_7d(self, request):
        """Items sold in the last 7 days, one bar per item (for bar chart)."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        result = _item_quantities_sold(start_date, end_date, limit=20)
        return Response(result)

    @action(detail=False, methods=['get'])
    def profit(self, request):
        """Calculate gross profit for today (revenue, cost, profit)."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sales = Sale.objects.filter(created_at__gte=today_start).prefetch_related(
            'sale_items__item',
            'sale_items__bundle__bundleitem_set__item',
        )

        revenue = sales.aggregate(Sum('total'))['total__sum'] or 0
        total_cost = 0
        for sale in sales:
            for cart_item in sale.sale_items.all():
                if cart_item.item_id:
                    total_cost += float(cart_item.item.wholesale_price) * cart_item.quantity
                elif cart_item.bundle_id:
                    for bi in cart_item.bundle.bundleitem_set.all():
                        total_cost += (
                            float(bi.item.wholesale_price)
                            * bi.quantity
                            * cart_item.quantity
                        )

        revenue = float(revenue)
        profit = revenue - total_cost

        return Response({
            "revenue": revenue,
            "cost": total_cost,
            "profit": profit
        })
