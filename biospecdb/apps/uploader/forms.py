from django import forms
from uploader.models import UploadedFile


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']