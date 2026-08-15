from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from .forms import OrganizationSignupForm


class OrganizationSignupView(View):
    template_name = "organizations/signup.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("pos:index")
        return render(request, self.template_name, {"form": OrganizationSignupForm()})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("pos:index")
        form = OrganizationSignupForm(request.POST)
        if form.is_valid():
            user, _organization = form.save()
            login(request, user)
            return redirect("pos:index")
        return render(request, self.template_name, {"form": form})


class OrganizationLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class OrganizationLogoutView(LogoutView):
    next_page = reverse_lazy("organizations:login")
