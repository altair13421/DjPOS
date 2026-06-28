from .organization_utils import get_user_organizations


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.organizations = []

        if request.user.is_authenticated:
            request.organizations = list(get_user_organizations(request.user))
            org_id = request.session.get("organization_id")
            if org_id:
                request.organization = next(
                    (org for org in request.organizations if org.pk == org_id),
                    None,
                )
            if request.organization is None and request.organizations:
                request.organization = request.organizations[0]
                request.session["organization_id"] = request.organization.pk

        return self.get_response(request)
