from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Category, Item, StockLog
from pos.models import Customer, Sale
from users.models import Organization, OrganizationMembership, Settings
from users.choices import OrganizationRole


class Command(BaseCommand):
    help = (
        "Create default groups (cashier, manager) with POS and inventory permissions."
    )

    ROLE_TO_GROUP = {
        OrganizationRole.OWNER: "manager",  # owners get manager-level perms
        OrganizationRole.MANAGER: "manager",
        OrganizationRole.CASHIER: "cashier",
    }

    @transaction.atomic
    def handle(self, *args, **options):
        cashier, _ = Group.objects.get_or_create(name="cashier")
        manager, _ = Group.objects.get_or_create(name="manager")
        owner, _ = Group.objects.get_or_create(name="owner")
        groups = {"cashier": cashier, "manager": manager, "owner": owner}

        sale_ct = ContentType.objects.get_for_model(Sale)
        customer_ct = ContentType.objects.get_for_model(Customer)
        item_ct = ContentType.objects.get_for_model(Item)
        category_ct = ContentType.objects.get_for_model(Category)
        stocklog_ct = ContentType.objects.get_for_model(StockLog)

        user_ct = ContentType.objects.get_for_model(User)
        settings_ct = ContentType.objects.get_for_model(Settings)
        user_perms = Permission.objects.filter(
            content_type__in=[user_ct],
            codename__in=["add_user", "change_user", "view_user"],
        )
        settings_perms = Permission.objects.filter(
            content_type__in=[settings_ct],
            codename__in=["add_settings", "change_settings", "view_settings"],
        )

        cashier_perms = Permission.objects.filter(
            content_type__in=[sale_ct, customer_ct],
            codename__in=[
                "add_sale",
                "change_sale",
                "view_sale",
                "add_customer",
                "view_customer",
            ],
        )

        manager_cts = [sale_ct, customer_ct, item_ct, category_ct, stocklog_ct]
        manager_perms = Permission.objects.filter(
            content_type__in=manager_cts,
        )

        owner_perms = manager_perms | user_perms | settings_perms

        cashier.permissions.set(cashier_perms)
        manager.permissions.set(manager_perms)
        owner.permissions.set(owner_perms)

        organization, _ = Organization.objects.get_or_create(
            name="Default Test", defaults={"is_active": False, "slug": "default-test"}
        )

        users = [
            {
                "first_name": "Test",
                "last_name": "Owner",
                "username": "testowner",
                "password": "ownerpassword",
                "email": "test@owner.com",
                "role": OrganizationRole.OWNER,
            },
            {
                "first_name": "Test",
                "last_name": "Manager",
                "username": "testmanager",
                "password": "managerpassword",
                "email": "test@manager.com",
                "role": OrganizationRole.MANAGER,
            },
            {
                "first_name": "Test",
                "last_name": "Cashier",
                "username": "testcashier",
                "password": "cashierpassword",
                "email": "test@cashier.com",
                "role": OrganizationRole.CASHIER,
            },
        ]

        owner_user = None
        created_summary = []
        for data in users:
            role = data.pop("role")

            user_, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "email": data["email"],
                },
            )
            if created:
                user_.set_password(data["password"])
                user_.save()

            OrganizationMembership.objects.get_or_create(
                user=user_,
                organization=organization,
                defaults={"role": role, "is_default": True},
            )

            # <-- this was missing: assign the Django group
            user_.groups.add(groups[self.ROLE_TO_GROUP[role]])

            if role == OrganizationRole.OWNER:
                owner_user = user_
            created_summary.append(f"{user_.username} ({role})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Groups ready: cashier, manager. Users: {', '.join(created_summary)}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Organization: {organization.name} (Active: {organization.is_active})"
            )
        )
        self.stdout.write(self.style.SUCCESS(f"users {users}"))
