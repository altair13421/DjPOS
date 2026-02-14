from django.db import models

class Customer(models.Model):
    """Customer for POS sales."""

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"Customer #{self.pk} - {self.name}"


class Cart(models.Model):
    """A cart for a sale."""

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def sold(self):
        return self.sale.pk is not None

    @property
    def total_price(self):
        return sum(item.item.unit_price * item.quantity for item in self.cart_items.all())

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cart #{self.pk} - {self.total_price} {self.created_at}"


class CartItem(models.Model):
    """An item in a cart."""

    item = models.ForeignKey("inventory.Item", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"CartItem #{self.pk} - {self.item.name} x {self.quantity}"


class Sale(models.Model):
    """A sale transaction."""

    cart = models.OneToOneField(Cart, on_delete=models.SET_NULL, null=True, related_name="sale")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sale #{self.pk} - {self.total_price} {self.created_at}"
