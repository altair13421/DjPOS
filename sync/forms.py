from django import forms

class SetupForm(forms.Form):
    central_url = forms.URLField(required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Url for sync"}))
    device_id = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Identifying Each Till Separately"}))
    device_key = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Key for encryption"}))
    organization = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Organization name"}))
    code = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Actual Code"}))

