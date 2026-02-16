from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from utils.stock_manager import StockManager

from .models import Customer, Sale
from .serializers import CustomerSerializer, SaleSerializer


def index(request):
    """Basic POS app index view."""
    return render(request, 'pos/index.html', {})

def terminal(request):
    """POS Terminal view."""
    return render(request, 'pos/terminal.html', {})


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related('customer').all()
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
