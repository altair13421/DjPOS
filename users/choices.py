from django.db import models
from django.utils.translation import gettext_lazy as _


class OrganizationRole(models.TextChoices):
    OWNER = "owner", _("Owner")
    MANAGER = "manager", _("Manager")
    CASHIER = "cashier", _("Cashier")

class UserLogReasons(models.TextChoices):
    SIGNIN = "SIGNIN", _("Signin")  # Can be The Same as Check in
    SIGNOUT = "SIGNOUT", _("Signout")  # Can be the Same as Check Out
    ACCESS = "ACCESS", _("Access")
    EDIT = "EDIT", _("Edit")
    CREATE = "CREATE", _("Create")
    CREATE_TERMINAL = "CREATE_TERMINAL", _("Create Terminal")
    DELETE_TERMINAL = "DELETE_TERMINAL", _("Delete Terminal")


class StoreCategoryChoices(models.TextChoices):
    RESTAURANT = "RESTAURANT", _("Restaurant")
    GENERAL_STORE = "GENERAL_STORE", _("General Store")
    DOLLAR_STORE = "DOLLAR_STORE", _("Dollar Store")
    APPAREL = "APPAREL", _("Apparel")
    GIFT_STORE = "GIFT_STORE", _("Gift Store")
