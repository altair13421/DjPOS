from django.urls import path, include
from . import setup_views, views

app_name = "sync"
urlpatterns = [
    path("setup/", setup_views.setup, name="setup_terminal"),
    path("ping/", setup_views.ping, name="ping_server"),
]