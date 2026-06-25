from django.core.management.base import BaseCommand
from django.db import transaction



class Command(BaseCommand):
    help = "Create Users, Groups and Bunch of Permissions."

    @transaction.atomic
    def handle(self, *args, **options):
         # Summary
        self.stdout.write(self.style.SUCCESS(
            "Created"
        )
    ))

