from django.urls import path, include
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/new/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("items/", views.ItemListView.as_view(), name="item_list"),
    path("items/new/", views.ItemCreateView.as_view(), name="item_create"),
    path("items/<int:pk>/edit/", views.ItemUpdateView.as_view(), name="item_edit"),
    path("api/", include([
        path("", views.ApiRootView.as_view(), name="api_root"),
        path("", include("inventory.api_urls")),
    ])),
]
