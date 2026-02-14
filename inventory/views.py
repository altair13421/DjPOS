from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Category, Item
from .serializers import CategorySerializer, ItemSerializer


def index(request):
    """Basic inventory app index view."""
    return render(request, 'inventory/index.html', {})


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related('category').all()
    serializer_class = ItemSerializer


@api_view(['GET'])
def api_root(request):
    """API root for inventory app."""
    return Response({
        'categories': request.build_absolute_uri('categories/'),
        'items': request.build_absolute_uri('items/'),
    })
