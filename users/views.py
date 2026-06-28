from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView

from .choices import OrganizationRole, UserLogReasons
from .forms import UserCreateForm
from .models import Organization, OrganizationMembership, UserLog
from .organization_utils import get_default_organization, set_session_organization


class UserLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        org = get_default_organization(self.request.user)
        if org:
            set_session_organization(self.request, org)
        UserLog.objects.create(
            user=self.request.user,
            reason=UserLogReasons.SIGNIN,
            organization=org,
        )
        return response


class UserLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            UserLog.objects.create(
                user=request.user,
                reason=UserLogReasons.SIGNOUT,
                organization=getattr(request, "organization", None),
            )
        return super().dispatch(request, *args, **kwargs)


class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("users:create")
    success_message = "User created."

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "Only staff can create users.")
        return super().handle_no_permission()

    def form_valid(self, form):
        response = super().form_valid(form)
        org = getattr(self.request, "organization", None)
        if org:
            OrganizationMembership.objects.get_or_create(
                user=self.object,
                organization=org,
                defaults={
                    "role": OrganizationRole.CASHIER,
                    "is_default": True,
                },
            )
        UserLog.objects.create(
            user=self.request.user,
            reason=UserLogReasons.CREATE,
            organization=org,
            notes=f"Created user {self.object.username}",
        )
        return response


@login_required
def select_organization(request):
    organizations = getattr(request, "organizations", [])
    if not organizations:
        return render(request, "users/no_organization.html")
    if len(organizations) == 1:
        set_session_organization(request, organizations[0])
        return redirect("pos:index")
    return render(
        request,
        "users/select_organization.html",
        {"organizations": organizations},
    )


@login_required
def switch_organization(request, slug):
    org = get_object_or_404(Organization, slug=slug, is_active=True)
    if not OrganizationMembership.objects.filter(
        user=request.user, organization=org
    ).exists():
        messages.error(request, "You do not have access to that organization.")
        return redirect("pos:index")
    set_session_organization(request, org)
    messages.success(request, f"Switched to {org.name}.")
    return redirect(request.META.get("HTTP_REFERER", reverse("pos:index")))
