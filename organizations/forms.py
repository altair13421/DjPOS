from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.forms import CharField, Form, TextInput, ValidationError
from django.utils.text import slugify

from .models import Organization, OrganizationMembership


class OrganizationSignupForm(Form):
    organization_name = CharField(
        max_length=255,
        widget=TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Organization / store name",
                "autofocus": True,
            }
        ),
        label="Organization name",
    )
    username = CharField(
        max_length=150,
        widget=TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
    )
    email = CharField(
        required=False,
        max_length=254,
        widget=TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email (optional)",
                "type": "email",
            }
        ),
        label="Email",
    )
    password1 = CharField(
        label="Password",
        widget=TextInput(
            attrs={
                "class": "form-control",
                "type": "password",
                "placeholder": "Password",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = CharField(
        label="Confirm password",
        widget=TextInput(
            attrs={
                "class": "form-control",
                "type": "password",
                "placeholder": "Confirm password",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_organization_name(self):
        name = self.cleaned_data["organization_name"].strip()
        if not name:
            raise ValidationError("Organization name is required.")
        return name

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two password fields didn’t match.")
        if password1:
            temp_user = User(username=cleaned.get("username") or "temp")
            try:
                validate_password(password1, temp_user)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def _unique_slug(self, name: str) -> str:
        base = slugify(name) or "organization"
        slug = base
        counter = 2
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def save(self):
        from django.db import transaction

        with transaction.atomic():
            organization = Organization.objects.create(
                name=self.cleaned_data["organization_name"],
                slug=self._unique_slug(self.cleaned_data["organization_name"]),
            )
            user = User.objects.create_user(
                username=self.cleaned_data["username"],
                email=self.cleaned_data.get("email") or "",
                password=self.cleaned_data["password1"],
            )
            OrganizationMembership.objects.create(
                organization=organization,
                user=user,
                role=OrganizationMembership.Role.OWNER,
            )
        return user, organization
