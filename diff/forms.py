from django import forms
from .models import Prototype


class Changes(forms.ModelForm):
    class Meta:
        model = Prototype
        fields = ["string_diff", ]
