from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from types import SimpleNamespace
from unittest.mock import Mock

from inventory.models import IngredientStock
from pos.models import Sale
from pos.views import SaleViewSet
from users.choices import OrganizationRole
from users.models import Organization, OrganizationMembership
from utils.stock_manager import StockManager
from . import payloads
from .auth import TerminalKeyAuth
from .api import DownloadView
from .models import CatalogVersion, OutboxRecord, Terminal


class TerminalKeyAuthTests(TestCase):
    def test_authenticated_terminal_is_available_on_request(self):
        organization = Organization.objects.create(name="Test", slug="test")
        terminal = Terminal.objects.create(
            organization=organization,
            name="Front counter",
            device_id="terminal-1",
            api_key="test-key",
        )
        request = Request(
            APIRequestFactory().get(
                "/",
                HTTP_X_DEVICE_ID=terminal.device_id,
                HTTP_X_DEVICE_KEY=terminal.api_key,
            )
        )

        authenticated_terminal, auth = TerminalKeyAuth().authenticate(request)

        self.assertIs(authenticated_terminal, terminal)
        self.assertIsNone(auth)
        self.assertIs(request.terminal, terminal)


class DownloadViewDebugSuperuserTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Debug Org", slug="debug-org"
        )
        self.terminal = Terminal.objects.create(
            organization=self.organization,
            name="Debug terminal",
            device_id="debug-terminal",
            api_key="debug-key",
        )

    def download(self):
        request = APIRequestFactory().get(
            "/sync/api/download/",
            HTTP_X_DEVICE_ID=self.terminal.device_id,
            HTTP_X_DEVICE_KEY=self.terminal.api_key,
        )
        return DownloadView.as_view()(request)

    def test_debug_superusers_are_not_synced_without_explicit_opt_in(self):
        User = get_user_model()
        User.objects.create_superuser(
            username="debug-admin", email="debug@example.com", password="password"
        )

        response = self.download()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["users"], [])

    def test_opted_in_org_syncs_unaffiliated_superusers_as_debug_owners(self):
        User = get_user_model()
        debug_user = User.objects.create_superuser(
            username="debug-admin", email="debug@example.com", password="password"
        )
        version = CatalogVersion.objects.get(organization=self.organization).value
        self.organization.allow_debug_superusers = True
        self.organization.save()

        response = self.download()

        self.assertGreater(
            CatalogVersion.objects.get(organization=self.organization).value, version
        )
        self.assertEqual(
            response.data["users"],
            [
                {
                    "username": debug_user.username,
                    "email": debug_user.email,
                    "password": debug_user.password,
                    "first_name": debug_user.first_name,
                    "last_name": debug_user.last_name,
                    "is_active": True,
                    "is_staff": True,
                    "is_superuser": True,
                    "role": OrganizationRole.OWNER,
                    "is_default": False,
                    "is_debug_access": True,
                }
            ],
        )

    def test_existing_membership_is_not_duplicated_or_promoted(self):
        User = get_user_model()
        debug_user = User.objects.create_superuser(
            username="debug-admin", email="debug@example.com", password="password"
        )
        OrganizationMembership.objects.create(
            user=debug_user,
            organization=self.organization,
            role=OrganizationRole.CASHIER,
        )
        self.organization.allow_debug_superusers = True
        self.organization.save()

        response = self.download()

        self.assertEqual(len(response.data["users"]), 1)
        self.assertEqual(response.data["users"][0]["role"], OrganizationRole.CASHIER)
        self.assertFalse(response.data["users"][0]["is_debug_access"])

    def test_removed_debug_access_revokes_orphaned_terminal_superuser(self):
        User = get_user_model()
        debug_user = User.objects.create_superuser(
            username="debug-admin", email="debug@example.com", password="password"
        )
        OrganizationMembership.objects.create(
            user=debug_user,
            organization=self.organization,
            role=OrganizationRole.OWNER,
            is_debug_access=True,
        )

        payloads.apply_catalog(
            {
                "organization": {
                    "pk": self.organization.pk,
                    "name": self.organization.name,
                    "slug": self.organization.slug,
                    "is_active": self.organization.is_active,
                },
                "users": [],
                "settings": None,
                "categories": [],
                "ingredients": [],
                "items": [],
                "item_ingredients": [],
                "bundles": [],
            }
        )

        debug_user.refresh_from_db()
        self.assertFalse(
            OrganizationMembership.objects.filter(
                user=debug_user, organization=self.organization
            ).exists()
        )
        self.assertFalse(debug_user.is_active)
        self.assertFalse(debug_user.is_staff)
        self.assertFalse(debug_user.is_superuser)


class OutgoingEventTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Sync Org", slug="sync-org"
        )

    def test_stock_adjustment_is_saved_on_server_without_enqueuing(self):
        ingredient = IngredientStock.objects.create(
            organization=self.organization, name="Flour", quantity=10
        )

        with override_settings(ROLE="server"):
            StockManager.restock_item(ingredient, 2)

        self.assertEqual(ingredient.stock_logs.count(), 1)
        self.assertEqual(OutboxRecord.objects.count(), 0)

    def test_terminal_stock_adjustment_is_saved_and_enqueued(self):
        ingredient = IngredientStock.objects.create(
            organization=self.organization, name="Flour", quantity=10
        )

        with override_settings(ROLE="terminal"):
            StockManager.restock_item(ingredient, 2)

        self.assertEqual(ingredient.stock_logs.count(), 1)
        self.assertEqual(
            OutboxRecord.objects.values_list("entity", flat=True).get(), "stock_adjust"
        )

    def test_terminal_stock_deduction_without_sale_is_enqueued(self):
        ingredient = IngredientStock.objects.create(
            organization=self.organization, name="Flour", quantity=10
        )

        with override_settings(ROLE="terminal"):
            StockManager.deduct_stock(ingredient, 2)

        self.assertEqual(ingredient.stock_logs.count(), 1)
        self.assertEqual(
            OutboxRecord.objects.values_list("entity", flat=True).get(), "stock_adjust"
        )

    def test_sale_is_enqueued_only_on_terminal(self):
        user = get_user_model().objects.create_user(username="cashier")
        def create_sale(**kwargs):
            return Sale.objects.create(total=10, **kwargs)

        serializer = Mock()
        serializer.save.side_effect = create_sale
        view = SaleViewSet()
        view.request = SimpleNamespace(organization=self.organization, user=user)

        with override_settings(ROLE="server"):
            view.perform_create(serializer)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(OutboxRecord.objects.count(), 0)

        with override_settings(ROLE="terminal"):
            view.perform_create(serializer)

        self.assertEqual(Sale.objects.count(), 2)
        self.assertEqual(
            OutboxRecord.objects.values_list("entity", flat=True).get(), "sale"
        )
