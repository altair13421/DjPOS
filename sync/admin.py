from django.contrib import admin

# Register your models here.
# Register All models
from .models import *

admin.site.register(Terminal)
admin.site.register(OutboxRecord)
admin.site.register(ReceivedEvent)
admin.site.register(CatalogVersion)
admin.site.register(PairingCode)
admin.site.register(SyncState)
