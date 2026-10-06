from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from django.db import transaction

from users.choices import OrganizationRole, StoreCategoryChoices, UserLogReasons
from users.models import Organization, OrganizationMembership, Settings, UserLog


class UserCreateForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email (optional)"}
        ),
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First name (optional)"}
        ),
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Last name (optional)"}
        ),
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="No group",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Optional role (e.g. cashier, manager).",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Username",
                    "autofocus": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Confirm password"}
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save()
            group = self.cleaned_data.get("group")
            if group:
                user.groups.add(group)
        return user


class BlankSignupForm(forms.Form):
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
                "autofocus": True,
            }
        ),
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First name (optional)"}
        ),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email (optional)"}
        ),
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Last name (optional)"}
        ),
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        ),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm password"}
        ),
    )

    # Organization name and slug fields
    organization_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Organization Name",
                "help_text": "Organization Name (e.g., Company, Store, etc.)",
            }
        ),
    )
    store_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Store Name",
                "help_text": "Any Store Name (Like, <City, branch, etc.)",
            }
        ),
    )
    store_address = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Store Address",
                "help_text": "Store Address",
            }
        ),
    )
    currency = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Currency",
                "value": "PKR",
                "help_text": "Currency for all amounts in the application (default: PKR)",
            }
        ),
    )
    owner_phone_number = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Owner Phone Number",
                "help_text": "Phone number of the Owner",
            }
        ),
    )
    store_category = forms.ChoiceField(
        required=True,
        choices=StoreCategoryChoices.choices,
        widget=forms.Select(
            attrs={"class": "form-select", "help_text": "Category of the Store"}
        ),
    )
    shift_duration = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Shift Duration (e.g., 8-hrs)",
                "help_text": "Duration of each shift (e.g., 8 hours)",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")

        return cleaned_data

    def save(self):
        # Create the user
        with transaction.atomic():
            user = User.objects.create_user(
                username=self.cleaned_data["username"],
                password=self.cleaned_data["password1"],
                email=self.cleaned_data.get("email", ""),
                first_name=self.cleaned_data.get("first_name", ""),
                last_name=self.cleaned_data.get("last_name", ""),
            )

            # Create the organization
            organization = Organization.objects.create(
                name=self.cleaned_data["organization_name"],
                slug=self.cleaned_data["organization_name"].lower().replace(" ", "-"),
                is_active=False,  # Set to False initially; can be activated later
            )

            # Create the settings for the organization
            Settings.objects.create(
                organization=organization,
                store_name=self.cleaned_data["store_name"],
                store_address=self.cleaned_data["store_address"],
                currency=self.cleaned_data["currency"],
                owner_name=f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}",
                owner_phone_number=self.cleaned_data["owner_phone_number"],
                store_category=self.cleaned_data["store_category"],
                shift_duration=self.cleaned_data["shift_duration"],
            )

            # Create the membership for the user in the organization
            OrganizationMembership.objects.create(
                user=user,
                organization=organization,
                role=OrganizationRole.OWNER,
                is_default=True,
            )

            log = UserLog.objects.create(
                user=user,
                reason=UserLogReasons.CREATE,
                organization=organization,
                user_role=OrganizationRole.OWNER,
                notes=f"Created organization {organization.name}, and Created user {user.username} as owner.",
            )

        return user, organization


class OrganizationSettingsForm(forms.ModelForm):
    organization_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Organization Name",
                "disabled": "disabled",
            }
        ),
    )

    class Meta:
        model = Settings
        fields = [
            "store_name",
            "store_address",
            "currency",
            "owner_name",
            "owner_phone_number",
            "store_category",
            "shift_duration",
        ]
