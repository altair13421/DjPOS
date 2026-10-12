import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import Bundle, BundleItem, Category, Item
from users.choices import OrganizationRole
from users.models import Organization, OrganizationMembership


class BundleCreateViewTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
            is_active=True,
        )
        user = get_user_model().objects.create_user(
            username="owner",
            password="test-password",
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=OrganizationRole.OWNER,
        )
        self.client.force_login(user)

    def test_created_bundle_is_assigned_to_current_organization(self):
        response = self.client.post(
            reverse("inventory:bundle_create"),
            {
                "name": "Test bundle",
                "price": "12.50",
                "active": "on",
                "items_json": "[]",
            },
        )

        self.assertRedirects(response, reverse("inventory:bundle_list"))
        bundle = Bundle.objects.get(name="Test bundle")
        self.assertEqual(bundle.organization, self.organization)

    def test_bundle_only_accepts_items_from_current_organization(self):
        other_organization = Organization.objects.create(
            name="Other Organization",
            slug="other-organization",
            is_active=True,
        )
        category = Category.objects.create(
            organization=other_organization,
            name="Other category",
        )
        other_item = Item.objects.create(
            organization=other_organization,
            name="Other item",
            sku="OTHER-1",
            category=category,
            wholesale_price=5,
        )

        response = self.client.post(
            reverse("inventory:bundle_create"),
            {
                "name": "Test bundle",
                "price": "12.50",
                "active": "on",
                "items_json": json.dumps([{"item_id": other_item.pk, "quantity": 1}]),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "All bundle items must belong to your current organization."
        )
        self.assertFalse(Bundle.objects.filter(name="Test bundle").exists())
        self.assertFalse(BundleItem.objects.exists())
