from enum import StrEnum, auto
import uuid

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

# Changes here need to be migrated, committed, and activated.
# See https://docs.djangoproject.com/en/4.2/intro/tutorial02/#activating-models
# python manage.py makemigrations uploader
# git add biospecdb/apps/uploader/migrations
# git commit -asm"Update uploader model(s)"
# python manage.py migrate
# python manage.py sqlmigrate uploader <migration_version>

POSITIVE = "positive"
NEGATIVE = "negative"


class UploadedFile(models.Model):
    file = models.FileField(upload_to='./biospecdb/apps/uploader/uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Patient(models.Model):
    MIN_AGE = 0
    MAX_AGE = 150

    class Gender(StrEnum):
        MALE = auto()
        FEMALE = auto()
        # NA = auto()  # ?

    patient_id = models.UUIDFIELD(unique=True, primary_key=True, default=uuid.uuid4, editable=False)
    gender = models.CharField(max_length=1, choices=Gender)


class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visit")
    previous_visit = models.ForeignKey("self", on_delete=models.SET_NULL(), related_name="next_visit")

    patient_age = models.IntegerField(validators=[MinValueValidator(Patient.MIN_AGE),
                                                  MaxValueValidator(Patient.MAX_AGE)])


class Disease(models.Model):
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=256)

    # This represents ths type/class for Symptom.disease_value.
    value_class = models.CharField(max_length=128, blank=True, null=True)


class Symptom(models.Model):
    MIN_SEVERITY = 0
    MAX_SEVERITY = 10

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="symptom")
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name="symptom")

    was_asked = models.BooleanField(default=True)
    is_symptomatic = models.BooleanField(default=True)
    days_symptomatic = models.IntegerField(default=0, null=True, validators=[MinValueValidator(0)])  # max <= age
    severity = models.IntegerField(default=10, validators=[MinValueValidator(MIN_SEVERITY),
                                                           MaxValueValidator(MAX_SEVERITY)],
                                   blank=True, null=True)

    # Str format for actual type/class spec'd by Disease.value_class.
    disease_value = models.CharField(blank=True, null=True, max_length=128)

# This is Model B wo/ disease table https://miro.com/app/board/uXjVMAAlj9Y=/
# class Symptoms(models.Model):
#     visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="symptoms")
#
#     # SARS-CoV-2 (COVID) viral load indicators.
#     Ct_gene_N = models.FloatField()
#     Ct_gene_ORF1ab = models.FloatField()
#     Covid_RT_qPCR = models.CharField(default=NEGATIVE, choices=(NEGATIVE, POSITIVE))
#     suspicious_contact = models.BooleanField(default=False)
#
#     # Symptoms/Diseases
#     fever = models.BooleanField(default=False)
#     dyspnoea = models.BooleanField(default=False)
#     oxygen_saturation_lt_95 = models.BooleanField(default=False)
#     cough = models.BooleanField(default=False)
#     coryza = models.BooleanField(default=False)
#     odinophagy = models.BooleanField(default=False)
#     diarrhea = models.BooleanField(default=False)
#     nausea = models.BooleanField(default=False)
#     headache = models.BooleanField(default=False)
#     weakness = models.BooleanField(default=False)
#     anosmia = models.BooleanField(default=False)
#     myalgia = models.BooleanField(default=False)
#     no_appetite = models.BooleanField(default=False)
#     vomiting = models.BooleanField(default=False)
#     chronic_pulmonary_inc_asthma = models.BooleanField(default=False)
#     cardiovascular_disease_inc_hypertension = models.BooleanField(default=False)
#     diabetes = models.BooleanField(default=False)
#     chronic_or_neuromuscular_neurological_disease = models.BooleanField(default=False)
#
#     more = models.JSONField()


class Instrument(models.Model):
    class Spectrometers(StrEnum):
        AGILENT_COREY_630 = auto()

    class SpectrometerCrystal(StrEnum):
        ZNSE = auto()

    spectrometer = models.CharField(default=Spectrometers.AGILENT_COREY_630, max_length=128, choices=Spectrometers)
    atr_crystal = models.CharField(default=SpectrometerCrystal.ZNSE, max_length=128, choices=SpectrometerCrystal)


class BioSample(models.Model):
    class SampleKind(StrEnum):
        PHARYNGEAL_SWAB = auto()

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="bio_sample")

    # Sample meta.
    sample_type = models.CharField(default=SampleKind.PHARYNGEAL_SWAB, max_length=128, choices=SampleKind)
    sample_processing = models.CharField(default="None", max_length=128)
    freezing_time = models.IntegerField(blank=True, null=True)
    thawing_time = models.IntegerField(blank=True, null=True)


class SpectralData(models.Model):
    class SpectralMeasurementKind(StrEnum):
        ATR_FTIR = auto()

    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="spectral_data")
    bio_sample = models.ForeignKey(BioSample, on_delete=models.CASCADE, related_name="spectral_data")

    # Spectrometer meta.
    spectra_measurement = models.CharField(default=SpectralMeasurementKind.ATR_FTIR, max_length=128,
                                           choices=SpectralMeasurementKind)
    acquisition_time = models.IntegerField(blank=True, null=True)
    n_coadditions = models.IntegerField(default=32)
    resolution = models.IntegerField(blank=True, null=True)

    qc_metrics = models.JSONField()  # TODO See https://github.com/ssec-jhu/biospecdb/issues/27

    # Spectral data.
    # TODO: We could write a custom storage class to write these all to a parquet table instead of individual files.
    # See https://docs.djangoproject.com/en/4.2/howto/custom-file-storage/
    data = models.FileField(upload_to="uploads/")
