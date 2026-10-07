from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("organization/", views.select_organization, name="select_organization"),
    path(
        "organization/users/logs/",
        views.UserLogListView.as_view(),
        name="organization_logs",
    ),
    path("organization/users/", views.UserListView.as_view(), name="user_list"),
    path(
        "organization/users/<int:pk>/",
        views.UserDetailView.as_view(),
        name="user_detail",
    ),
    path(
        "organization/users/create/", views.UserCreateView.as_view(), name="user_create"
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
    path(
        "organization/create/",
        views.OrganizationCreateView.as_view(),
        name="organization_create_by_user",
    ),
    path(
        "signup",
        views.OrganizationBlankCreateView.as_view(),
        name="organization_create",
    ),
]
