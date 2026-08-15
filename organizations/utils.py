from django.contrib.auth import get_user_model
from django.db import models


def get_user_organization(user):
    """Return the primary organization for an authenticated user, or None."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    membership = (
        user.organization_memberships.select_related("organization")
        .order_by("created_at")
        .first()
    )
    return membership.organization if membership else None


def require_user_organization(user):
    organization = get_user_organization(user)
    if organization is None:
        raise models.ObjectDoesNotExist("User has no organization membership.")
    return organization


def organization_queryset(model, user):
    """Filter a model queryset to the user's organization."""
    organization = get_user_organization(user)
    if organization is None:
        return model.objects.none()
    return model.objects.filter(organization=organization)
