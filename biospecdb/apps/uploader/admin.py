from django.contrib import admin
from .models import BioSample, Disease, Instrument, Patient, SpectralData, Symptom, UploadedFile, Visit

admin.site.register(BioSample)
admin.site.register(Disease)
admin.site.register(Instrument)
admin.site.register(Patient)
admin.site.register(SpectralData)
admin.site.register(Symptom)
admin.site.register(Visit)

admin.site.register(UploadedFile)