from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .choices import OrganizationRole
from .models import Organization, OrganizationMembership, Settings


class OrganizationSettingsTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Store", slug="test-store", is_active=True
        )
        self.user = User.objects.create_user(username="owner", password="test-pass")
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationRole.OWNER,
        )
        self.settings = Settings.objects.create(
            organization=self.organization,
            store_name="Old Store Name",
            store_address="Old address",
            owner_phone_number="555-0100",
        )
        self.client.force_login(self.user)
        from django.urls import reverse

        self.url = reverse("users:general_settings")

    @override_settings(ROLE="server")
    def test_owner_can_update_general_settings(self):
        response = self.client.post(
            self.url,
            {
                "store_name": "New Store Name",
                "store_address": "New address",
                "owner_phone_number": "555-0199",
                "store_category": "RESTAURANT",
                "shift_duration": "6 hours",
            },
        )

        self.assertRedirects(response, self.url)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.store_name, "New Store Name")
        self.assertEqual(self.settings.store_address, "New address")
        self.assertEqual(self.settings.owner_phone_number, "555-0199")
        self.assertEqual(self.settings.store_category, "RESTAURANT")
        self.assertEqual(self.settings.shift_duration, "6 hours")

    @override_settings(ROLE="terminal")
    def test_terminal_settings_page_is_read_only(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "read-only on this terminal")
        self.assertNotContains(response, "Save settings")

    @override_settings(ROLE="terminal")
    def test_terminal_cannot_change_settings(self):
        response = self.client.post(
            self.url,
            {
                "store_name": "Not saved",
                "store_address": "",
                "owner_phone_number": "555-0199",
                "store_category": "RESTAURANT",
                "shift_duration": "6 hours",
            },
        )

        self.assertRedirects(response, self.url)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.store_name, "Old Store Name")

    @override_settings(ROLE="server")
    def test_non_owner_cannot_open_general_settings(self):
        OrganizationMembership.objects.filter(user=self.user).update(
            role=OrganizationRole.MANAGER
        )

        response = self.client.get(self.url)

        self.assertRedirects(response, "/pos/")


class UserSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="staff", password="Initial-pass-741!"
        )
        self.organization = Organization.objects.create(
            name="Profile Store", slug="profile-store", is_active=True
        )
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationRole.CASHIER,
        )
        self.client.force_login(self.user)
        self.url = reverse("users:user_settings")

    @override_settings(ROLE="server")
    def test_user_can_view_and_update_own_profile(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile Store")
        self.assertContains(response, "staff")

        response = self.client.post(
            self.url,
            {
                "action": "profile",
                "first_name": "Taylor",
                "last_name": "User",
                "email": "taylor@example.com",
            },
        )

        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Taylor")
        self.assertEqual(self.user.last_name, "User")
        self.assertEqual(self.user.email, "taylor@example.com")

    @override_settings(ROLE="server")
    def test_password_change_keeps_user_logged_in(self):
        response = self.client.post(
            self.url,
            {
                "action": "password",
                "old_password": "Initial-pass-741!",
                "new_password1": "Changed-pass-852!",
                "new_password2": "Changed-pass-852!",
            },
        )

        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Changed-pass-852!"))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    @override_settings(ROLE="terminal")
    def test_terminal_profile_and_password_edits_are_read_only(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "read-only on this terminal")
        self.assertNotContains(response, "Save profile")

        response = self.client.post(
            self.url,
            {
                "action": "profile",
                "first_name": "Not saved",
                "last_name": "",
                "email": "",
            },
        )

        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")
