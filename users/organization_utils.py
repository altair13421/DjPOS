from django.contrib.auth.models import User

from .models import Organization, OrganizationMembership
from .choices import OrganizationRole

def get_user_organizations(user: User):
    if not user.is_authenticated:
        return Organization.objects.none()
    return Organization.objects.filter(
        memberships__user=user,
        is_active=True,
    ).distinct()


def get_default_organization(user: User):
    membership = (
        OrganizationMembership.objects.filter(user=user, is_default=True)
        .select_related("organization")
        .first()
    )
    if membership:
        return membership.organization
    membership = (
        OrganizationMembership.objects.filter(user=user)
        .select_related("organization")
        .first()
    )
    return membership.organization if membership else None


def set_session_organization(request, organization: Organization):
    request.session["organization_id"] = organization.pk
    request.organization = organization

def get_user_role_in_organization(user: User, organization: Organization):
    membership = OrganizationMembership.objects.filter(
        user=user, organization=organization
    ).first()
    return membership.role if membership else None

def get_roles_with_lower_priority(role):
    current_priority = role.priority()
    return [r for r in OrganizationRole if r.priority() <= current_priority]
