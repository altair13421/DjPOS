from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("signup/", views.OrganizationSignupView.as_view(), name="signup"),
    path("login/", views.OrganizationLoginView.as_view(), name="login"),
    path("logout/", views.OrganizationLogoutView.as_view(), name="logout"),
]
