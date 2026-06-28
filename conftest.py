import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from users.models import Organization, OrganizationMembership


@pytest.fixture
def organization(db):
    org, _ = Organization.objects.get_or_create(
        slug="default",
        defaults={"name": "Default Organization"},
    )
    return org


@pytest.fixture
def user(db, organization):
    user = User.objects.create_user(username="testuser", password="testpass123")
    OrganizationMembership.objects.get_or_create(
        user=user,
        organization=organization,
        defaults={"role": "owner", "is_default": True},
    )
    return user


@pytest.fixture
def api_client(user, organization):
    client = APIClient()
    client.force_login(user)
    session = client.session
    session["organization_id"] = organization.pk
    session.save()
    return client
