from django.db import models
from .choices import StockChangeReason, StockAddedAs

class Category(models.Model):
    """Product category for inventory items."""

    name = models.CharField(max_length=255)
    identifier = models.CharField(max_length=100, unique=True, default="")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "categories"

    def __str__(self):
        return f"Category #{self.pk} - {self.name}"

    def save(self, *args, **kwargs):
        if self.identifier == "":
            self.identifier = self.name.upper()[:4]
        super().save(*args, **kwargs)

class IngredientStock(models.Model):
    """The Actual Ingredients go here, Hence The STOCK"""

    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    retail_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_as = models.CharField(
        max_length=32,
        null=True,
        choices=StockAddedAs.choices,
        default=StockAddedAs.STOCK,
    )
    item_id = models.IntegerField(
        default=0
    )


    @property
    def check_availability(self):
        return quantity > 0


class Item(models.Model):
    """Inventory item (product)."""

    name = models.CharField(max_length=255)
    sku = models.CharField(
        max_length=100, unique=True
    )  # Stock Keeping Unit. A unique identifier for the item.
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    retail_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ingredients = models.ManyToManyField(IngredientStock, through="ItemIngredient", related_name="ingredients")

    @property
    def total_wholesale(self):
        return sum([ing.ingredient.wholesale_price for ing in self.itemingredient_set.select_related('ingredient').all()])

    @property
    def check_availability(self):
        return self.availability_count > 0

    @property
    def availability_count(self):
        availabilities = [ing.availability_count for ing in self.itemingredient_set.select_related("ingredient").all()]
        return min(availabilities)

    @classmethod
    def count(cls):
        return cls.objects.count()

    def save(self, *args, **kwargs):
        if self.sku == "":
            self.sku = f"{self.category.identifier}-0{self.count()}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Item #{self.pk} - {self.name}"

class ItemIngredient(models.Model):
    ingredient = models.ForeignKey(IngredientStock, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(default=1, max_digits=12, decimal_places=2, null=True)

    def __str__(self):
        return f"{self.ingredient.name} x {self.quantity} in {self.item.name}"

    @property
    def check_availability(self):
        return self.availability_count > 0

    @property
    def availability_count(self):
        return self.ingredient.quantity // self.quantity


class Bundle(models.Model):
    """A bundle of items sold together."""
    name = models.CharField(max_length=255)
    items = models.ManyToManyField(Item, through='BundleItem', related_name='bundles')
    price = models.DecimalField(max_digits=12, decimal_places=2)  # The deal price
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_wholesale(self):
        return sum(
            bi.item.wholesale_price * bi.quantity
            for bi in self.bundleitem_set.select_related('item').all()
        )

    @property
    def total_retail(self):
        return sum(
            bi.item.retail_price * bi.quantity
            for bi in self.bundleitem_set.select_related('item').all()
        )

    @property
    def check_availability(self):
        return self.availability_count > 0

    @property
    def availability_count(self):
        return min([bi.availability_count for bi in self.bundleitem_set.select_related("item").all()])


    # for item in Bundle.objects.all():print(item, item.check_availability, item.availability_count)
    def __str__(self):
        return f"Bundle: {self.name} (PKR {self.price})"


class BundleItem(models.Model):
    """Intermediate model for Bundle-Item relationship."""
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(default=1, max_digits=12, decimal_places=2,)

    @property
    def check_availability(self):
        return self.availability_count > 0

    @property
    def availability_count(self):
        return self.item.availability_count // self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.item.name} in {self.bundle.name}"


class StockLog(models.Model):
    """Log of stock changes."""
    item = models.ForeignKey(IngredientStock, on_delete=models.CASCADE, related_name='stock_logs')
    change_quantity = models.IntegerField()  # Positive for add, negative for remove
    reason = models.CharField(max_length=50, choices=StockChangeReason.choices)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name}: {self.change_quantity} ({self.get_reason_display()})"
