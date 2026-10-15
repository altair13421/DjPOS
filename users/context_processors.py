from django.conf import settings

from .choices import OrganizationRole
from .organization_utils import get_user_role_in_organization


def organization_context(request):
    organization = getattr(request, "organization", None)
    role = (
        get_user_role_in_organization(request.user, organization)
        if request.user.is_authenticated and organization
        else None
    )
    return {
        "current_organization": organization,
        "user_organizations": getattr(request, "organizations", []),
        "can_access_general_settings": (
            role == OrganizationRole.OWNER
        ),
        "can_edit_general_settings": (
            role == OrganizationRole.OWNER and settings.ROLE != "terminal"
        ),
    }

from django.conf import settings

if settings.ROLE == "terminal":
    def terminal_context(request):
        return {
            "organization": getattr(settings, "ORGANIZATION_NAME", "DJPOS")
        }
