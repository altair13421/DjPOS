from django.db import models
from decimal import Decimal

# Create your models here.

# Not Declaring, But Only reminding myself to call them from here.

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry

from .choices import StoreCategoryChoices, UserLogReasons

class Settings(models.Model):
    store_name = models.CharField(max_length=127, default="DJPOS")
    store_address = models.TextField()
    currency = models.CharField(max_length=127, default="PKR")
    owner_name = models.CharField(max_length=127, default="YEAGER")
    owner_phone_number = models.CharField(max_length=31, default="+92-321-748-0678")

    store_category = models.CharField(
        max_length=31, default=StoreCategoryChoices.GENERAL_STORE, choices=StoreCategoryChoices.choices
    )
    shift_duration = models.CharField(max_length=31, default="8-hrs")


class UserLog(models.Model):
    reason = models.CharField(max_length=127, default=UserLogReasons.SIGNIN, choices=UserLogReasons.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    details = models.JSONField(blank=True)

