from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Category, Item, StockLog
from pos.models import Customer, Sale


class Command(BaseCommand):
    help = "Create default groups (cashier, manager) with POS and inventory permissions."

    @transaction.atomic
    def handle(self, *args, **options):
        cashier, _ = Group.objects.get_or_create(name="cashier")
        manager, _ = Group.objects.get_or_create(name="manager")

        sale_ct = ContentType.objects.get_for_model(Sale)
        customer_ct = ContentType.objects.get_for_model(Customer)
        item_ct = ContentType.objects.get_for_model(Item)
        category_ct = ContentType.objects.get_for_model(Category)
        stocklog_ct = ContentType.objects.get_for_model(StockLog)

        cashier_perms = Permission.objects.filter(
            content_type__in=[sale_ct, customer_ct],
            codename__in=["add_sale", "change_sale", "view_sale", "add_customer", "view_customer"],
        )
        manager_perms = Permission.objects.filter(
            content_type__in=[sale_ct, customer_ct, item_ct, category_ct, stocklog_ct],
        )

        cashier.permissions.set(cashier_perms)
        manager.permissions.set(manager_perms)

        self.stdout.write(self.style.SUCCESS("Created groups: cashier, manager"))
