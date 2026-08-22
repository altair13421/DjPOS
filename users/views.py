from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .choices import OrganizationRole, UserLogReasons
from .forms import UserCreateForm
from .models import Organization, OrganizationMembership, UserLog
from .organization_utils import (
    get_default_organization,
    set_session_organization,
    get_user_role_in_organization,
    get_roles_with_lower_priority,
)
from .mixins import OrgLoginAndRoleRequiredMixin


class UserLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        org = get_default_organization(self.request.user)
        if org:
            set_session_organization(self.request, org)
        if self.request.user.is_superuser:
            return redirect("/admin/")

        UserLog.objects.create(
            user=self.request.user,
            reason=UserLogReasons.SIGNIN,
            user_role=(
                get_user_role_in_organization(self.request.user, org) if org else None
            ),
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
                user_role=(
                    get_user_role_in_organization(
                        request.user, getattr(request, "organization", None)
                    )
                    if getattr(request, "organization", None)
                    else None
                ),
            )
        return super().dispatch(request, *args, **kwargs)


class UserCreateView(
    OrgLoginAndRoleRequiredMixin, SuccessMessageMixin, CreateView
):
    model = User
    form_class = UserCreateForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("users:create")
    success_message = "User created."

    required_roles = [OrganizationRole.OWNER, OrganizationRole.MANAGER]

    def handle_no_permission(self):
        messages.error(self.request, "Only Staff/Owner can create users.")
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
            user_role=(
                get_user_role_in_organization(self.request.user, org) if org else None
            ),
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


class UserLogListView(OrgLoginAndRoleRequiredMixin, ListView):
    model = UserLog
    template_name = "users/userlog_list.html"
    context_object_name = "userlogs"
    paginate_by = 20

    required_roles = [OrganizationRole.OWNER, OrganizationRole.MANAGER]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        queryset = UserLog.objects.filter(
            organization=org,
            user_role=get_roles_with_lower_priority(
                get_user_role_in_organization(self.request.user, org)
            ),
        ).order_by("-created_at")
        return queryset


class UserLogDetailView( OrgLoginAndRoleRequiredMixin, DetailView):
    model = UserLog
    template_name = "users/userlog_detail.html"
    context_object_name = "userlog"

    required_roles = [OrganizationRole.OWNER, OrganizationRole.MANAGER]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        userlog_id = self.kwargs.get("pk")
        queryset = UserLog.objects.filter(organization=org, id=userlog_id).order_by(
            "-created_at"
        )
        return queryset
