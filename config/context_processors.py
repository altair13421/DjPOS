from organizations.utils import get_user_organization


def app_settings(request):
    from django.conf import settings

    organization = None
    if getattr(request, "user", None) is not None:
        organization = get_user_organization(request.user)

    return {
        "SHOW_API_UI": getattr(settings, "SHOW_API_UI", False),
        "CURRENT_ORGANIZATION": organization,
    }
