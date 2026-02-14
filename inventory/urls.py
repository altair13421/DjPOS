from django.urls import path, include
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.index),
    path('api/', include([
        path('', views.api_root, name='api_root'),
        path('', include('inventory.api_urls')),
    ])),
]
