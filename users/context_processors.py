def organization_context(request):
    return {
        "current_organization": getattr(request, "organization", None),
        "user_organizations": getattr(request, "organizations", []),
    }
