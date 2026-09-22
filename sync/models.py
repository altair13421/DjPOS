import secrets, uuid
from django.conf import settings
from django.db import models
from users.models import Organization

class Terminal(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="terminals")
    device_id = models.CharField(max_length=64, unique=True)
    name      = models.CharField(max_length=120)
    api_key   = models.CharField(max_length=64, unique=True, default=secrets.token_hex)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)

class OutboxRecord(models.Model):       # terminal side — the queue
    event_id  = models.UUIDField(default=uuid.uuid4, unique=True)
    entity    = models.CharField(max_length=30)          # "sale" | "userlog" | "stock_adjust"
    payload   = models.JSONField()
    queued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    pushed_at = models.DateTimeField(null=True, blank=True, db_index=True)

class ReceivedEvent(models.Model):      # central side — the dedupe log
    event_id    = models.UUIDField(unique=True)
    terminal    = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    entity      = models.CharField(max_length=30)
    received_at = models.DateTimeField(auto_now_add=True)

class CatalogVersion(models.Model):     # PER ORG — each tenant's catalog changes independently
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    value        = models.BigIntegerField(default=0)

class SyncState(models.Model):          # terminal bookkeeping (one till = one DB, so one row)
    key   = models.CharField(max_length=50, primary_key=True)
    value = models.CharField(max_length=200)

