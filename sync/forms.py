from django import forms

class SetupForm(forms.Form):
    central_url = forms.URLField(required=True)
    device_id = forms.CharField(max_length=255, required=True)
    device_key = forms.CharField(max_length=255, required=True)
    organization = forms.CharField(max_length=255, required=True)
    code = forms.CharField(max_length=255, required=True)

