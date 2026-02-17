from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from utils.stock_manager import StockManager

from .models import Customer, Sale
from .serializers import CustomerSerializer, SaleSerializer


def index(request):
    """Basic POS app index view."""
    return render(request, 'pos/index.html', {})


def sale_panel(request):
    """POS sale_panel view."""
    return render(request, 'pos/sale_panel.html', {
        'use_web_print': getattr(settings, 'USE_WEB_PRINT', True),
    })


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
        'use_web_print': getattr(settings, 'USE_WEB_PRINT', True),
    })


def receipt(request, sale_id):
    """Thermal-styled receipt view for web print (opens in new window)."""
    sale = get_object_or_404(
        Sale.objects.select_related('customer').prefetch_related(
            'sale_items__item', 'sale_items__bundle'
        ),
        pk=sale_id,
    )
    return render(request, 'pos/receipt.html', {
        'sale': sale,
        'store_name': getattr(settings, 'RECEIPT_STORE_NAME', 'DJPOS'),
        'currency': getattr(settings, 'CURRENCY_CODE', 'PKR'),
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

    @action(detail=True, methods=["post"], url_path="print_receipt")
    def print_receipt(self, request, pk=None):
        """Send receipt to direct thermal printer (when USE_WEB_PRINT is False)."""
        if getattr(settings, 'USE_WEB_PRINT', True):
            return Response(
                {"error": "Direct printing is disabled (USE_WEB_PRINT is True). Use the receipt page to print."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sale = self.get_object()
        try:
            self._print_receipt_direct(sale)
            return Response({"status": "ok", "message": "Receipt sent to printer."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except OSError as e:
            return Response(
                {"error": f"Could not reach printer: {e}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @staticmethod
    def _print_receipt_direct(sale):
        from utils.receipt_escpos import build_receipt, send_to_printer
        host = getattr(settings, 'PRINTER_HOST', '').strip()
        if not host:
            raise ValueError("PRINTER_HOST is not set. Configure it for direct thermal printing.")
        port = getattr(settings, 'PRINTER_PORT', 9100)
        store = getattr(settings, 'RECEIPT_STORE_NAME', 'DJPOS')
        currency = getattr(settings, 'CURRENCY_CODE', 'PKR')
        data = build_receipt(sale, store_name=store, currency=currency)
        send_to_printer(data, host, port)


@api_view(['GET'])
def api_root(request):
    """API root for pos app."""
    return Response({
        'customers': request.build_absolute_uri('customers/'),
        'sales': request.build_absolute_uri('sales/'),
    })
