from django.conf import settings
from django.db import models
from .choices import CustomerType


class Customer(models.Model):
    """Customer for POS sales."""

    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="customers",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    type_cus = models.CharField(max_length=50, blank=True, default=CustomerType.WALK_IN)

    class Meta:
        """Meta class for the Customer model."""

        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["name"]

    def __str__(self):
        return f"Customer #{self.pk} - {self.name} - {self.type_cus}"


class CartItem(models.Model):
    """An item or bundle in a cart. Exactly one of item or bundle must be set."""

    item = models.ForeignKey(
        "inventory.Item",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    bundle = models.ForeignKey(
        "inventory.Bundle",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )  # Price at time of sale (item or bundle)
    sale = models.ForeignKey(
        "Sale", on_delete=models.CASCADE, related_name="sale_items"
    )
    stock_before = models.PositiveIntegerField(null=True, blank=True)
    stock_after = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True)

    class Meta:
        """Meta class for the CartItem model."""

        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ["-created_at"]

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        if self.bundle_id:
            return f"CartItem #{self.pk} - {self.bundle.name} x {self.quantity}"
        return f"CartItem #{self.pk} - {self.item.name} x {self.quantity}"


class Sale(models.Model):
    """A sale transaction."""

    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="sales",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True)

    @property
    def total_price(self):
        return self.total - self.discount - self.tax

    class Meta:
        """Meta class for the Sale model."""

        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sale #{self.pk} - {self.total_price} {self.created_at}"
