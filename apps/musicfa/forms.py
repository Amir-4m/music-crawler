from django import forms

from ckeditor.widgets import CKEditorWidget

from .models import CMusic


class CMusicForm(forms.ModelForm):
    lyrics = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = CMusic
        fields = '__all__'
