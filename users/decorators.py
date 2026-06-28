from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


def org_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "organization", None):
            return redirect(reverse("users:select_organization"))
        return view_func(request, *args, **kwargs)

    return wrapper
