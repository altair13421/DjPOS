from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('categories', views.CategoryViewSet, basename='category')
router.register('items', views.ItemViewSet, basename='item')
router.register('bundles', views.BundleViewSet, basename='bundle')
router.register('stock_logs', views.StockLogViewSet, basename='stock_log')

urlpatterns = [
    path('', include(router.urls)),
]
