from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.permissions import IsAuthenticated

from organizations.utils import get_user_organization


class OrganizationRequiredMixin(LoginRequiredMixin):
    """Ensure the user is authenticated and belongs to an organization."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        organization = get_user_organization(request.user)
        if organization is None:
            from django.contrib.auth import logout
            from django.shortcuts import redirect

            logout(request)
            return redirect("organizations:login")
        request.organization = organization
        return super().dispatch(request, *args, **kwargs)

    def get_organization(self):
        return getattr(self.request, "organization", None) or get_user_organization(
            self.request.user
        )


class OrganizationQuerysetMixin(OrganizationRequiredMixin):
    """Filter CBVs by the current user's organization."""

    organization_field = "organization"

    def get_queryset(self):
        qs = super().get_queryset()
        organization = self.get_organization()
        if organization is None:
            return qs.none()
        return qs.filter(**{self.organization_field: organization})


class OrganizationFormMixin(OrganizationQuerysetMixin):
    """Assign organization on create and scope related form querysets."""

    def form_valid(self, form):
        if hasattr(form.instance, "organization_id") and not form.instance.organization_id:
            form.instance.organization = self.get_organization()
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        organization = self.get_organization()
        if organization is None:
            return form
        if "category" in form.fields and hasattr(form.fields["category"], "queryset"):
            form.fields["category"].queryset = form.fields["category"].queryset.filter(
                organization=organization
            )
        return form


class IsOrganizationMember(IsAuthenticated):
    """DRF permission requiring an organization membership."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return get_user_organization(request.user) is not None


class OrganizationViewSetMixin:
    """Mixin for DRF viewsets scoped to the requester's organization."""

    permission_classes = [IsOrganizationMember]
    organization_field = "organization"

    def get_organization(self):
        return get_user_organization(self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization"] = self.get_organization()
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        organization = self.get_organization()
        if organization is None:
            return qs.none()
        return qs.filter(**{self.organization_field: organization})

    def perform_create(self, serializer):
        organization = self.get_organization()
        serializer.save(**{self.organization_field: organization})
