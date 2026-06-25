from django.db import models
from decimal import Decimal

# Create your models here.

# Not Declaring, But Only reminding myself to call them from here.

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry

class Settings(models.Model):
    store_name = models.CharField(max_length=127, default="DJPOS")
    store_address = models.TextField()
    currency = models.CharField(max_length=127, default="PKR")
    owner_name = models.CharField(max_length=127, default="YEAGER")
    owner_phone_number = models.CharField(max_length=31, default="+92-321-748-0678")

    shift_duration = models.CharField(max_length=31, default="8-hrs")


