from django.db import models
from .choices import StockChangeReason

# TODO:
# - Suggestions Tab will give Suggestions on how many are low stocked. 
#   Like chicken or Cheese is low stocked, please buy some more.

class Category(models.Model):
    """Product category for inventory items."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    identifier = models.CharField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if self.identifier == "":
            self.identifier = f"{self.name[:4].upper()}"
        super().save(*args, **kwargs)

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
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # quanitiy_type = models.CharField(max_length=255, default="metric")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    retail_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    is_ingredient = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


    def save(self, *args, **kwargs):
        if self.sku == "":
            count = self.counter()
            count += 1
            self.sku = f"{self.category.identifier}-0{count}"
        if self.quantity == 0:
            self.is_active = False
        super().save(*args, **kwargs)

    @property
    def is_available(self) -> bool:
        return self.quantity >= 0

    @classmethod
    def counter(cls) -> int:
        return cls.objects.count()

    def __str__(self):
        return f"Item #{self.pk} - {self.name}"


class Bundle(models.Model):
    """A bundle of items sold together."""
    name = models.CharField(max_length=255)
    items = models.ManyToManyField("self", through='BundleItem', related_name='bundles', symmetrical=False)
    price = models.DecimalField(max_digits=12, decimal_places=2)  # The deal price
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_available(self):
        bundle_items = BundleItem.objects.filter(bundle=self).select_related("item", "bundle_included")
        bundle_available = True
        for bi in bundle_items:
            if bi.item and bi.item.is_available:
                item_available = bi.item.quantity >= bi.quantity
            if bi.bundle_included:
                bundle_available = bundle_available and bi.bundle_included.is_available
        return item_available and bundle_available

    @property
    def how_many_available(self):
        bundle_items = BundleItem.objects.filter(bundle=self).select_related("item", "bundle_included")
        possible_counts = []
        for bi in bundle_items:
            if bi.item and bi.item.is_available:
                items_available = bi.item.quantity // bi.quantity # Integer Division
                possible_counts.append(items_available)
            if bi.bundle_included:
                bundle_available = bi.bundle_included.how_many_available
                possible_counts.append(bundle_available // bi.quantity)
        return min(possible_counts) if possible_counts else 0

    @property
    def total_wholesale(self):
        wholesale = 0
        bundleitems = BundleItem.objects.filter(bundle=self)
        for bi in bundleitems.all():
            if bi.item:
                wholesale += bi.item.wholesale_price * bi.quantity
            if bi.bundle_included:
                wholesale += bi.bundle_included.total_wholesale * bi.quantity
        return wholesale

    @property
    def bundle_items(self):
        return self.bundleitem_set.select_related('item', 'bundle_included').all()

    @property
    def total_retail(self):
        retail_price = 0
        bundleitems = BundleItem.objects.filter(bundle=self)
        for bi in bundleitems.all():
            if bi.item:
                retail_price += bi.item.retail_price * bi.quantity
            if bi.bundle_included:
                retail_price += bi.bundle_included.total_retail * bi.quantity
        return retail_price

    @property
    def requires(self):
        return [bi.item_data for bi in self.bundleitem_set.select_related('item').all()]

    def __str__(self):
        return f"Bundle: {self.name} (PKR {self.price})"


class BundleItem(models.Model):
    """Intermediate model for Bundle-Item relationship.""" 
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    bundle_included = models.ForeignKey(Bundle, null=True, blank=True, on_delete=models.SET_NULL, related_name="included_by")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)

    @property
    def item_data(self):
        return {
            'name': self.item.name,
            'quantity': self.quantity,
            'wholesale_price': self.item.wholesale_price,
            'retail_price': self.item.retail_price,
        }

    def consume_stock(self):
        self.item.quantity -= self.quantity
        for bundle in self.bundle_included.bundleitem_set.all():
            bundle.consume_stock()
        self.item.save()
        self.save()

    @property
    def retail_price(self):
        price = 0
        if self.item:
            price += self.item.retail_price
        elif self.bundle_included:
            price += self.bundle_included.total_retail
        return price
    def __str__(self):
        return f"{self.quantity} x {self.item.name if self.item else ''} {self.bundle_included.name if self.bundle_included else ''} in {self.bundle.name}"


class StockLog(models.Model):
    """Log of stock changes."""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='stock_logs')
    change_quantity = models.IntegerField()  # Positive for add, negative for remove
    reason = models.CharField(max_length=50, choices=StockChangeReason.choices)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name}: {self.change_quantity} ({self.get_reason_display()})"
