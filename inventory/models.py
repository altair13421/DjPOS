from django.db import models
from django.db.models import UniqueConstraint

from .choices import StockChangeReason


class Category(models.Model):
    """Product category for inventory items."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    identifier = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "categories"
        constraints = [
            UniqueConstraint(
                fields=["organization", "identifier"],
                name="uniq_category_org_identifier",
            )
        ]

    def save(self, *args, **kwargs):
        if self.identifier == "":
            self.identifier = f"{self.name[:4].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Category #{self.pk} - {self.name}"


class Item(models.Model):
    """Inventory item (product)."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    retail_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    is_ingredient = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            UniqueConstraint(
                fields=["organization", "sku"],
                name="uniq_item_org_sku",
            )
        ]

    def save(self, *args, **kwargs):
        if self.sku == "":
            count = (
                type(self)
                .objects.filter(organization_id=self.organization_id)
                .count()
                + 1
            )
            prefix = self.category.identifier if self.category_id else "ITEM"
            self.sku = f"{prefix}-0{count}"
        if self.quantity == 0:
            self.is_active = False
        super().save(*args, **kwargs)

    @property
    def is_available(self) -> bool:
        return self.quantity > 0

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.reorder_level

    def __str__(self):
        return f"Item #{self.pk} - {self.name}"


class Bundle(models.Model):
    """A bundle of items sold together."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="bundles",
    )
    name = models.CharField(max_length=255)
    items = models.ManyToManyField(
        "self", through="BundleItem", related_name="bundles", symmetrical=False
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_available(self):
        bundle_items = BundleItem.objects.filter(bundle=self).select_related(
            "item", "bundle_included"
        )
        item_available = True
        bundle_available = True
        for bi in bundle_items:
            if bi.item_id:
                item_available = item_available and (
                    bi.item.is_available and bi.item.quantity >= bi.quantity
                )
            if bi.bundle_included_id:
                bundle_available = bundle_available and bi.bundle_included.is_available
        return item_available and bundle_available

    @property
    def how_many_available(self):
        bundle_items = BundleItem.objects.filter(bundle=self).select_related(
            "item", "bundle_included"
        )
        possible_counts = []
        for bi in bundle_items:
            if bi.item_id and bi.item.is_available and bi.quantity:
                possible_counts.append(bi.item.quantity // bi.quantity)
            if bi.bundle_included_id and bi.quantity:
                possible_counts.append(
                    bi.bundle_included.how_many_available // bi.quantity
                )
        return min(possible_counts) if possible_counts else 0

    @property
    def total_wholesale(self):
        wholesale = 0
        for bi in BundleItem.objects.filter(bundle=self):
            if bi.item_id:
                wholesale += bi.item.wholesale_price * bi.quantity
            if bi.bundle_included_id:
                wholesale += bi.bundle_included.total_wholesale * bi.quantity
        return wholesale

    @property
    def bundle_items(self):
        return self.bundleitem_set.select_related("item", "bundle_included").all()

    @property
    def total_retail(self):
        retail_price = 0
        for bi in BundleItem.objects.filter(bundle=self):
            if bi.item_id:
                retail_price += bi.item.retail_price * bi.quantity
            if bi.bundle_included_id:
                retail_price += bi.bundle_included.total_retail * bi.quantity
        return retail_price

    @property
    def requires(self):
        return [
            bi.item_data
            for bi in self.bundleitem_set.select_related("item").all()
            if bi.item_id
        ]

    def __str__(self):
        return f"Bundle: {self.name} (PKR {self.price})"


class BundleItem(models.Model):
    """Intermediate model for Bundle-Item relationship."""

    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    bundle_included = models.ForeignKey(
        Bundle,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="included_by",
    )
    quantity = models.PositiveIntegerField(default=1)

    @property
    def item_data(self):
        if not self.item_id:
            return {}
        return {
            "name": self.item.name,
            "quantity": self.quantity,
            "wholesale_price": self.item.wholesale_price,
            "retail_price": self.item.retail_price,
        }

    def consume_stock(self):
        if self.item_id:
            self.item.quantity -= self.quantity
            self.item.save()
        if self.bundle_included_id:
            for nested in self.bundle_included.bundleitem_set.all():
                nested.consume_stock()

    @property
    def retail_price(self):
        price = 0
        if self.item_id:
            price += self.item.retail_price
        elif self.bundle_included_id:
            price += self.bundle_included.total_retail
        return price

    def __str__(self):
        item_name = self.item.name if self.item_id else ""
        nested_name = self.bundle_included.name if self.bundle_included_id else ""
        return f"{self.quantity} x {item_name} {nested_name} in {self.bundle.name}"


class StockLog(models.Model):
    """Log of stock changes."""

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stock_logs")
    change_quantity = models.IntegerField()
    reason = models.CharField(max_length=50, choices=StockChangeReason.choices)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name}: {self.change_quantity} ({self.get_reason_display()})"
