from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from pos.models import Sale, CartItem
from inventory.models import Item

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
        """Top selling items."""
        items = CartItem.objects.filter(sale__isnull=False).values(
            'item__name'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]
        
        return Response(items)

    @action(detail=False, methods=['get'])
    def profit(self, request):
        """Calculate gross profit for today (revenue, cost, profit)."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sales = Sale.objects.filter(created_at__gte=today_start).prefetch_related('sale_items__item')

        revenue = sales.aggregate(Sum('total'))['total__sum'] or 0
        total_cost = 0
        for sale in sales:
            for cart_item in sale.sale_items.all():
                total_cost += cart_item.item.cost_price * cart_item.quantity

        revenue = float(revenue)
        total_cost = float(total_cost)
        profit = revenue - total_cost

        return Response({
            "revenue": revenue,
            "cost": total_cost,
            "profit": profit
        })
