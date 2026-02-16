from django.urls import path, include
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.index, name='index'),
    path('sale_panel/', views.sale_panel, name='sale_panel'),
    path('sale_history/', views.sale_history, name='sale_history'),
    path('api/', include([
        path('', views.api_root, name='api_root'),
        path('', include('pos.api_urls')),
    ])),
]
