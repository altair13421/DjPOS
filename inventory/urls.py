from django.urls import path, include
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("stats/", views.InventoryStatsView.as_view(), name="stats"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/new/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("items/", views.ItemListView.as_view(), name="item_list"),
    path("items/new/", views.ItemCreateView.as_view(), name="item_create"),
    path("items/<int:pk>/edit/", views.ItemUpdateView.as_view(), name="item_edit"),
    path("bundles/", views.BundleListView.as_view(), name="bundle_list"),
    path("bundles/new/", views.BundleCreateView.as_view(), name="bundle_create"),
    path("bundles/<int:pk>/edit/", views.BundleUpdateView.as_view(), name="bundle_edit"),
    path("bundles/<int:pk>/delete/", views.BundleDeleteView.as_view(), name="bundle_delete"),
    path("api/", include([
        path("", views.ApiRootView.as_view(), name="api_root"),
        path("", include("inventory.api_urls")),
    ])),
]
