from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from inventory.models import Bundle, Category, Item
from users.models import Organization


class FillSampleInventoryAdminTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.organization = Organization.objects.create(
            name="Sample Organization",
            slug="sample-organization",
        )
        self.client.force_login(self.admin_user)

    def test_category_admin_has_button_to_add_samples(self):
        response = self.client.get(reverse("admin:inventory_category_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add dummy inventory")

    def test_non_superuser_cannot_use_sample_inventory_page(self):
        staff_user = get_user_model().objects.create_user(
            username="staff",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse("admin:inventory_category_fill_samples"))

        self.assertEqual(response.status_code, 403)

    @override_settings(ROLE="terminal")
    def test_terminal_cannot_use_sample_inventory_page(self):
        response = self.client.get(reverse("admin:inventory_category_fill_samples"))

        self.assertEqual(response.status_code, 403)

    def test_sample_button_populates_selected_organization_idempotently(self):
        url = reverse("admin:inventory_category_fill_samples")
        response = self.client.post(
            url,
            {"organization": self.organization.pk},
        )

        self.assertRedirects(response, reverse("admin:inventory_category_changelist"))
        self.assertEqual(
            Category.objects.filter(organization=self.organization).count(), 3
        )
        self.assertEqual(
            Item.objects.filter(organization=self.organization).count(), 8
        )
        self.assertEqual(
            Bundle.objects.filter(organization=self.organization).count(), 2
        )

        self.client.post(url, {"organization": self.organization.pk})

        self.assertEqual(
            Category.objects.filter(organization=self.organization).count(), 3
        )
        self.assertEqual(
            Item.objects.filter(organization=self.organization).count(), 8
        )
        self.assertEqual(
            Bundle.objects.filter(organization=self.organization).count(), 2
        )

    def test_sample_button_requires_valid_organization(self):
        response = self.client.post(
            reverse("admin:inventory_category_fill_samples"),
            {"organization": 99999},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Category.objects.count(), 0)
