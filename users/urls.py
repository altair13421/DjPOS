from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("create/", views.UserCreateView.as_view(), name="create"),
    path("organization/", views.select_organization, name="select_organization"),
    path(
        "organization/logs/", views.UserLogListView.as_view(), name="organization_logs"
    ),
    path(
        "organization/logs/<int:pk>/",
        views.UserLogDetailView.as_view(),
        name="userlog_detail",
    ),
    path(
        "organization/switch/<slug:slug>/",
        views.switch_organization,
        name="switch_organization",
    ),
]
