from django.conf import settings
from django.db import models


class Organization(models.Model):
    """A tenant that owns POS and inventory data."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    """Links a user to an organization with a role."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.OWNER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="uniq_organization_user_membership",
            )
        ]
        ordering = ["organization__name", "user__username"]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.role})"
