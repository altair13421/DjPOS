from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse


class OrganizationRequiredMixin:
    """Require an active organization on the request."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not getattr(request, "organization", None):
            return redirect(reverse("users:select_organization"))
        return super().dispatch(request, *args, **kwargs)


class OrganizationScopedMixin:
    """Filter querysets and assign organization on create."""

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is None:
            return qs.none()
        return qs.filter(organization=org)

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        return super().get_object(queryset=queryset)

    def form_valid(self, form):
        if hasattr(form.instance, "organization_id") and not form.instance.organization_id:
            form.instance.organization = self.request.organization
        return super().form_valid(form)


class OrgLoginRequiredMixin(LoginRequiredMixin, OrganizationRequiredMixin):
    pass
