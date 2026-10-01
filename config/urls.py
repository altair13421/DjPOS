"""
URL configuration for DJPOS project.
"""

from django.views.generic.base import RedirectView
from django.contrib import admin
from django.urls import path, include

from sync import terminal_admin, setup_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls")),
    path("pos/", include("pos.urls")),
    path("inventory/", include("inventory.urls")),
    path("", RedirectView.as_view(url="/pos/")),
]
from django.conf import settings

# Server Routes only
if settings.ROLE == "server":
    urlpatterns += [
        path("api/sync/", include("sync.api_urls")),
        path("terminals/", terminal_admin.terminals, name="terminals"),
    ]
if settings.ROLE == "terminal":
    urlpatterns += [
        path("sync/", include("sync.urls")),
    ]