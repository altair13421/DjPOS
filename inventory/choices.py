from django.db import models
from django.utils.translation import gettext_lazy as _

class StockChangeReason(models.TextChoices):
    SALE = "SALE", _("Sale")
    RESTOCK = "RESTOCK", _("Restock")
    WASTE = "WASTE", _("Waste")
    RETURN = "RETURN", _("Return")
