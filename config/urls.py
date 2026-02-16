"""
URL configuration for OSPOS project.
"""
from django.views.generic.base import RedirectView
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('pos/', include('pos.urls')),
    path('inventory/', include('inventory.urls')),
    path('', RedirectView.as_view(url='/pos/')),
]
