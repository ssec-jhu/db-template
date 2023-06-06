from django.contrib import admin
from .models import Patient, BioSample, UploadedFile

admin.site.register(Patient)
admin.site.register(BioSample)
admin.site.register(UploadedFile)
