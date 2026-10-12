from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.choices import StockChangeReason
from inventory.models import IngredientStock, StockLog
from users.models import Organization, OrganizationMembership


class StockLogViewTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Stock log org",
            slug="stock-log-org",
            is_active=True,
        )
        self.user = get_user_model().objects.create_user(
            username="stock-log-user",
            password="test-password",
        )
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role="owner",
            is_default=True,
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["organization_id"] = self.organization.pk
        session.save()
        self.stock = IngredientStock.objects.create(
            organization=self.organization,
            name="Coffee beans",
            quantity=20,
        )

    def test_stock_logs_page_lists_only_the_current_organization(self):
        StockLog.objects.create(
            organization=self.organization,
            item=self.stock,
            change_quantity=5,
            reason=StockChangeReason.RESTOCK,
            note="Delivery",
            performed_by=self.user,
        )
        other_organization = Organization.objects.create(
            name="Other stock log org",
            slug="other-stock-log-org",
            is_active=True,
        )
        other_stock = IngredientStock.objects.create(
            organization=other_organization,
            name="Private stock",
        )
        StockLog.objects.create(
            organization=other_organization,
            item=other_stock,
            change_quantity=-3,
            reason=StockChangeReason.SALE,
            note="Should not appear",
        )

        response = self.client.get(reverse("inventory:stock_logs"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coffee beans")
        self.assertContains(response, "Delivery")
        self.assertNotContains(response, "Private stock")
        self.assertNotContains(response, "Should not appear")

    def test_stock_logs_page_filters_by_reason_and_item(self):
        StockLog.objects.create(
            organization=self.organization,
            item=self.stock,
            change_quantity=5,
            reason=StockChangeReason.RESTOCK,
        )
        StockLog.objects.create(
            organization=self.organization,
            item=self.stock,
            change_quantity=-2,
            reason=StockChangeReason.WASTE,
        )

        response = self.client.get(
            reverse("inventory:stock_logs"),
            {"reason": StockChangeReason.WASTE, "item": self.stock.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["stock_logs"]), 1)
        self.assertEqual(
            response.context["stock_logs"][0].reason,
            StockChangeReason.WASTE,
        )
