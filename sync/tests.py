from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from inventory.choices import StockChangeReason
from inventory.models import IngredientStock, Item, StockLog
from pos.models import CartItem, Sale
from pos.views import SaleViewSet
from users.choices import OrganizationRole
from users.models import Organization, OrganizationMembership
from utils.stock_manager import StockManager
from . import engine, payloads
from .auth import TerminalKeyAuth
from .api import DownloadView, SalesHistoryView
from .models import CatalogVersion, OutboxRecord, Terminal, get_state, set_state


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


class SalesHistorySyncTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Sales Org", slug="sales-org"
        )
        self.terminal = Terminal.objects.create(
            organization=self.organization,
            name="Sales terminal",
            device_id="sales-terminal",
            api_key="sales-key",
        )
        self.ingredient = IngredientStock.objects.create(
            organization=self.organization,
            name="Flour",
            quantity=8,
        )
        self.item = Item.objects.create(
            organization=self.organization,
            name="Bread",
            sku="BREAD-1",
        )

    def make_sale(self):
        sale = Sale.objects.create(
            organization=self.organization,
            device_id="server",
            total=10,
            paid=10,
        )
        CartItem.objects.create(
            sale=sale,
            item=self.item,
            quantity=1,
            unit_price=10,
        )
        StockLog.objects.create(
            organization=self.organization,
            item=self.ingredient,
            change_quantity=-2,
            reason=StockChangeReason.SALE,
            sale=sale,
        )
        return sale

    def request_history(self, after=0):
        request = APIRequestFactory().get(
            "/sync/api/sales-history/",
            {"after": after},
            HTTP_X_DEVICE_ID=self.terminal.device_id,
            HTTP_X_DEVICE_KEY=self.terminal.api_key,
        )
        return SalesHistoryView.as_view()(request)

    def test_history_endpoint_scopes_and_paginates_by_organization(self):
        first_sale = self.make_sale()
        self.make_sale()
        other_org = Organization.objects.create(name="Other Org", slug="other-org")
        Sale.objects.create(organization=other_org, total=20)

        with patch("sync.api.SALES_HISTORY_BATCH_SIZE", 1):
            first_page = self.request_history()
            second_page = self.request_history(first_page.data["next_cursor"])

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data["organization_id"], self.organization.pk)
        self.assertEqual(len(first_page.data["sales"]), 1)
        self.assertEqual(first_page.data["sales"][0]["uuid"], str(first_sale.uuid))
        self.assertFalse(first_page.data["complete"])
        self.assertEqual(len(second_page.data["sales"]), 1)
        self.assertTrue(second_page.data["complete"])

    def test_history_rejects_invalid_cursor(self):
        response = self.request_history(after="-1")

        self.assertEqual(response.status_code, 400)

    def test_import_restores_sale_without_reapplying_stock_delta_and_is_idempotent(self):
        source_sale = self.make_sale()
        sale_data = payloads.freeze_sale(source_sale)
        source_sale.delete()

        imported = payloads.apply_sales_history([sale_data], self.organization)
        imported_again = payloads.apply_sales_history([sale_data], self.organization)

        self.assertEqual(imported, 1)
        self.assertEqual(imported_again, 0)
        self.assertEqual(Sale.objects.filter(uuid=sale_data["uuid"]).count(), 1)
        self.assertEqual(CartItem.objects.filter(sale__uuid=sale_data["uuid"]).count(), 1)
        self.assertEqual(StockLog.objects.filter(sale__uuid=sale_data["uuid"]).count(), 1)
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity, 8)
        self.assertEqual(OutboxRecord.objects.count(), 0)

    def test_history_pull_persists_progress_and_runs_only_once(self):
        source_sale = self.make_sale()
        sale_data = payloads.freeze_sale(source_sale)
        source_sale.delete()
        response = Mock()
        response.json.return_value = {
            "organization_id": self.organization.pk,
            "sales": [sale_data],
            "next_cursor": 12,
            "complete": True,
        }
        set_state("sales_history_cursor", "0")
        set_state("sales_history_complete", "false")
        device_config = {
            "central_url": "https://central.example",
            "device_id": self.terminal.device_id,
            "device_key": self.terminal.api_key,
        }

        with (
            patch("sync.engine.config.device_config", return_value=device_config),
            patch("sync.engine.SESSION.get", return_value=response) as get,
        ):
            self.assertEqual(engine.pull_sales_history(), 1)
            self.assertEqual(engine.pull_sales_history(), 0)

        self.assertEqual(get.call_count, 1)
        self.assertEqual(get_state("sales_history_cursor"), "12")
        self.assertEqual(get_state("sales_history_complete"), "true")
        self.assertEqual(Sale.objects.filter(uuid=sale_data["uuid"]).count(), 1)


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


class CatalogApplyTests(TestCase):
    def test_pull_creates_zero_wholesale_item_before_restoring_catalog_price(self):
        organization = Organization.objects.create(
            name="Catalog Org", slug="catalog-org"
        )
        payloads.apply_catalog(
            {
                "organization": {
                    "pk": organization.pk,
                    "name": organization.name,
                    "slug": organization.slug,
                    "is_active": True,
                },
                "users": [],
                "settings": None,
                "categories": [
                    {
                        "uuid": "11111111-1111-4111-8111-111111111111",
                        "name": "Bakery",
                        "identifier": "BAKE",
                        "description": "",
                    }
                ],
                "ingredients": [
                    {
                        "uuid": "22222222-2222-4222-8222-222222222222",
                        "name": "Flour",
                        "quantity": "10",
                        "wholesale_price": "2",
                        "retail_price": "3",
                        "added_as": "STOCK",
                        "item_id": 0,
                    }
                ],
                "items": [
                    {
                        "uuid": "33333333-3333-4333-8333-333333333333",
                        "name": "Bread",
                        "sku": "BAKE-001",
                        "category": "11111111-1111-4111-8111-111111111111",
                        "cost_price": "4",
                        "retail_price": "8",
                        "wholesale_price": "0",
                    }
                ],
                "item_ingredients": [
                    {
                        "uuid": "44444444-4444-4444-8444-444444444444",
                        "item": "33333333-3333-4333-8333-333333333333",
                        "ingredient": "22222222-2222-4222-8222-222222222222",
                        "quantity": "1",
                    }
                ],
                "bundles": [],
            }
        )

        item = Item.objects.get(uuid="33333333-3333-4333-8333-333333333333")
        self.assertEqual(item.wholesale_price, 0)
        self.assertEqual(item.itemingredient_set.count(), 1)
