from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomerType(models.TextChoices):
    WALK_IN = "WALK_IN", _("Walk in")
    TAKEAWAY = "TAKEAWAY", _("Takeaway")

