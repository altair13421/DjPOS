from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Category, Item, StockLog
from pos.models import Customer, Sale
from users.models import Organization, OrganizationMembership
from users.choices import OrganizationRole


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

        # Create a Basic default Organization
        # And a User that is a an Admin there. and give him organization ownership.

        organization, _ = Organization.objects.get_or_create(name="Default Test", is_active=False)
        users = [{
            "first_name": "Test",
            "last_name": "Owner",
            "username": "testowner",
            "password": "ownerpassword",
            "email": "test@owner.com",
            "role": OrganizationRole.OWNER,
        },{
            "first_name": "Test",
            "last_name": "Manager",
            "username": "testmanager",
            "password": "managerpassword",
            "email": "test@manager.com",
            "role": OrganizationRole.MANAGER,
        }, {
            "first_name": "Test",
            "last_name": "Cashier",
            "username": "testcashier",
            "password": "cashierpassword",
            "email": "test@cashier.com",
            "role": OrganizationRole.CASHIER,
        }]
        for user in users:
            role = user.pop("role")
            user_ = User.objects.create_user(
                **user
            )
            org_mem, _ = OrganizationMembership.objects.get_or_create(
                user = user_,
                organization=organization,
                defaults={"role":role, "is_default": True}
            )

        self.stdout.write(self.style.SUCCESS(f"Created groups: cashier, manager, and Users: {users}"))

