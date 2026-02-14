from django.db import models


class Category(models.Model):
    """Product category for inventory items."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "categories"

    def __str__(self):
        return f"Category #{self.pk} - {self.name}"


class Item(models.Model):
    """Inventory item (product)."""

    name = models.CharField(max_length=255)
    sku = models.CharField(
        max_length=100, unique=True, blank=True
    )  # Stock Keeping Unit. A unique identifier for the item.
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Item #{self.pk} - {self.name}"
