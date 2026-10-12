def organization_context(request):
    return {
        "current_organization": getattr(request, "organization", None),
        "user_organizations": getattr(request, "organizations", []),
    }

from django.conf import settings

if settings.ROLE == "terminal":
    def terminal_context(request):
        return {
            "organization": getattr(settings, "ORGANIZATION_NAME", "DJPOS")
        }
