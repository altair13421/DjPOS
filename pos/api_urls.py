from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('customers', views.CustomerViewSet, basename='customer')
router.register('sales', views.SaleViewSet, basename='sale')

urlpatterns = [
    path('', include(router.urls)),
]
