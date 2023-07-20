from django import forms
from uploader.models import UploadedFile


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["meta_data_file", "spectral_data_file"]
