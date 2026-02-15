from django import forms
from .models import Category, Item


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category name"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description"}
            ),
        }


class ItemForm(forms.ModelForm):
    """Item form with optional 'add category on same page' via new_category_name."""

    new_category_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Or type a new category name to create and assign",
            }
        ),
        label="New category (optional)",
    )

    class Meta:
        model = Item
        fields = ["name", "sku", "category", "quantity", "retail_price", "wholesale_price"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Item name"}),
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "SKU (optional)"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "retail_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": "0.01"}
            ),
            "wholesale_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "— No category —"
        self.fields["category"].queryset = Category.objects.all().order_by("name")

    def clean(self):
        data = super().clean()
        new_name = (data.get("new_category_name") or "").strip()
        category = data.get("category")
        if new_name and category:
            self.add_error(
                "new_category_name",
                "Choose either an existing category or a new category name, not both.",
            )
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_name = (self.cleaned_data.get("new_category_name") or "").strip()
        if new_name:
            category, _ = Category.objects.get_or_create(
                name=new_name,
                defaults={"description": ""},
            )
            instance.category = category
        if commit:
            instance.save()
        return instance
