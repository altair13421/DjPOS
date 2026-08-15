from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from organizations.mixins import IsOrganizationMember, OrganizationViewSetMixin
from organizations.utils import get_user_organization
from utils.stock_manager import StockManager

from .models import Customer, Sale
from .serializers import CustomerSerializer, SaleSerializer


def _require_organization(request):
    organization = get_user_organization(request.user)
    if organization is None:
        from django.contrib.auth import logout

        logout(request)
        return None
    return organization


@login_required
def index(request):
    """Basic POS app index view."""
    if _require_organization(request) is None:
        return redirect("organizations:login")
    return render(request, "pos/index.html", {})


@login_required
def sale_panel(request):
    """POS sale_panel view."""
    if _require_organization(request) is None:
        return redirect("organizations:login")
    return render(
        request,
        "pos/sale_panel.html",
        {
            "use_web_print": getattr(settings, "USE_WEB_PRINT", True),
        },
    )


@login_required
def sale_history(request):
    """Sale history with date range filter: 1d, 7d, 30d, all."""
    organization = _require_organization(request)
    if organization is None:
        return redirect("organizations:login")

    now = timezone.now()
    range_param = request.GET.get("range", "7d")
    range_labels = {
        "1d": "1 day",
        "7d": "7 days",
        "30d": "1 month",
        "all": "All time",
    }

    qs = (
        Sale.objects.filter(organization=organization)
        .select_related("customer")
        .prefetch_related("sale_items__item", "sale_items__bundle")
        .order_by("-created_at")
    )

    if range_param == "1d":
        qs = qs.filter(created_at__gte=now - timedelta(days=1))
    elif range_param == "7d":
        qs = qs.filter(created_at__gte=now - timedelta(days=7))
    elif range_param == "30d":
        qs = qs.filter(created_at__gte=now - timedelta(days=30))

    return render(
        request,
        "pos/sale_history.html",
        {
            "sales": list(qs),
            "range_param": range_param,
            "range_labels": range_labels,
            "use_web_print": getattr(settings, "USE_WEB_PRINT", True),
        },
    )


@login_required
def receipt(request, sale_id):
    """Thermal-styled receipt view for web print (opens in new window)."""
    organization = _require_organization(request)
    if organization is None:
        return redirect("organizations:login")

    sale = get_object_or_404(
        Sale.objects.filter(organization=organization)
        .select_related("customer")
        .prefetch_related("sale_items__item", "sale_items__bundle"),
        pk=sale_id,
    )
    return render(
        request,
        "pos/receipt.html",
        {
            "sale": sale,
            "store_name": getattr(settings, "RECEIPT_STORE_NAME", "DJPOS"),
            "currency": getattr(settings, "CURRENCY_CODE", "PKR"),
        },
    )


class CustomerViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class SaleViewSet(OrganizationViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        Sale.objects.select_related("customer")
        .prefetch_related("sale_items__item", "sale_items__bundle")
        .all()
    )
    serializer_class = SaleSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = self.get_organization()
        return context

    def perform_create(self, serializer):
        sale = serializer.save()
        StockManager.process_sale(sale)

    @action(detail=True, methods=["post"], url_path="print_receipt")
    def print_receipt(self, request, pk=None):
        """Send receipt to direct thermal printer (when USE_WEB_PRINT is False)."""
        if getattr(settings, "USE_WEB_PRINT", True):
            return Response(
                {
                    "error": "Direct printing is disabled (USE_WEB_PRINT is True). Use the receipt page to print."
                },
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

        host = getattr(settings, "PRINTER_HOST", "").strip()
        if not host:
            raise ValueError(
                "PRINTER_HOST is not set. Configure it for direct thermal printing."
            )
        port = getattr(settings, "PRINTER_PORT", 9100)
        store = getattr(settings, "RECEIPT_STORE_NAME", "DJPOS")
        currency = getattr(settings, "CURRENCY_CODE", "PKR")
        data = build_receipt(sale, store_name=store, currency=currency)
        send_to_printer(data, host, port)


@api_view(["GET"])
@permission_classes([IsOrganizationMember])
def api_root(request):
    """API root for pos app."""
    return Response(
        {
            "customers": request.build_absolute_uri("customers/"),
            "sales": request.build_absolute_uri("sales/"),
        }
    )
