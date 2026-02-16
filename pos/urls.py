from django.urls import path, include
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.index, name='index'),
    path('sale_panel/', views.sale_panel, name='sale_panel'),
    path('api/', include([
        path('', views.api_root, name='api_root'),
        path('', include('pos.api_urls')),
    ])),
]
