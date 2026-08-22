from django.db import models
from django.contrib.auth.models import User

from .choices import StoreCategoryChoices, UserLogReasons, OrganizationRole


class Organization(models.Model):
    name = models.CharField(max_length=127)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=False)
    # Plan to be included.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if self.slug == "":
            self.slug = self.name.lower().replace(" ", "-")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(
        max_length=31,
        choices=OrganizationRole.choices,
        default=OrganizationRole.CASHIER,
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = [("user", "organization")]

    def __str__(self):
        return f"{self.user.username} @ {self.organization.name} ({self.role})"


class Settings(models.Model):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    store_name = models.CharField(max_length=127, default="DJPOS")
    store_address = models.TextField(default="")
    currency = models.CharField(max_length=127, default="PKR")
    owner_name = models.CharField(max_length=127, default="YEAGER")
    owner_phone_number = models.CharField(max_length=31, default="+92-321-748-0678")
    store_category = models.CharField(
        max_length=31,
        default=StoreCategoryChoices.GENERAL_STORE,
        choices=StoreCategoryChoices.choices,
    )
    shift_duration = models.CharField(max_length=31, default="8-hrs")


class UserLog(models.Model):
    reason = models.CharField(
        max_length=127, default=UserLogReasons.SIGNIN, choices=UserLogReasons.choices
    )
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="user_logs",
        null=True,
        blank=True,
    )
    user_role = models.CharField(
        max_length=31, choices=OrganizationRole.choices, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    details = models.JSONField(blank=True, default=dict)
