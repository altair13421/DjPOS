from django import forms

class SetupForm(forms.Form):
    central_url = forms.URLField(required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Url for sync"}))
    code = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Actual Code"}))

