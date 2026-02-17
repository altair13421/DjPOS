from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from utils.stock_manager import StockManager

from .models import Customer, Sale
from .serializers import CustomerSerializer, SaleSerializer


def index(request):
    """Basic POS app index view."""
    return render(request, 'pos/index.html', {})


def sale_panel(request):
    """POS sale_panel view."""
    return render(request, 'pos/sale_panel.html', {})


def sale_history(request):
    """Sale history with date range filter: 1d, 7d, 30d, all."""
    now = timezone.now()
    range_param = request.GET.get('range', '7d')
    range_labels = {'1d': '1 day', '7d': '7 days', '30d': '1 month', 'all': 'All time'}

    qs = Sale.objects.select_related('customer').prefetch_related(
        'sale_items__item', 'sale_items__bundle'
    ).order_by('-created_at')

    if range_param == '1d':
        start = now - timedelta(days=1)
        qs = qs.filter(created_at__gte=start)
    elif range_param == '7d':
        start = now - timedelta(days=7)
        qs = qs.filter(created_at__gte=start)
    elif range_param == '30d':
        start = now - timedelta(days=30)
        qs = qs.filter(created_at__gte=start)
    # 'all' or anything else: no filter

    sales = list(qs)
    return render(request, 'pos/sale_history.html', {
        'sales': sales,
        'range_param': range_param,
        'range_labels': range_labels,
    })


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related('customer').prefetch_related(
        'sale_items__item', 'sale_items__bundle'
    ).all()
    serializer_class = SaleSerializer

    def perform_create(self, serializer):
        sale = serializer.save()
        StockManager.process_sale(sale)


@api_view(['GET'])
def api_root(request):
    """API root for pos app."""
    return Response({
        'customers': request.build_absolute_uri('customers/'),
        'sales': request.build_absolute_uri('sales/'),
    })
