from django.contrib import admin

from .models import Patient, BioSample

admin.site.register(Patient)
admin.site.register(BioSample)
