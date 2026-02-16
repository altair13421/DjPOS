from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api.analytics import AnalyticsViewSet

router = DefaultRouter()
router.register('customers', views.CustomerViewSet, basename='customer')
router.register('sales', views.SaleViewSet, basename='sale')
router.register('analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
]
