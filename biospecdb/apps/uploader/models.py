from enum import auto
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

import biospecdb.util
from .loaddata import save_data_to_db


# Changes here need to be migrated, committed, and activated.
# See https://docs.djangoproject.com/en/4.2/intro/tutorial02/#activating-models
# python manage.py makemigrations uploader
# git add biospecdb/apps/uploader/migrations
# git commit -asm"Update uploader model(s)"
# python manage.py migrate
# python manage.py sqlmigrate uploader <migration_version>

POSITIVE = "positive"
NEGATIVE = "negative"

# https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/index.html
# NOTE: Examples of PHI:
# Medical record number.
# Health plan beneficiary number.
# Device identifiers or serial numbers.
# An MRI scan.
# Blood test results.
# Any other unique identifying numbers, characteristics, or codes.

# The following PII is considered PHI when accompanied by health data (i.e., as it would be for this project).
# Name.
# Address (including subdivisions smaller than state such as street address, city, county, or zip code).
# All elements of dates (except year) for dates that are directly related to an individual, including birth date,
# admission date, discharge date, death date, and all ages over 89 and all elements of dates (including year)
# indicative of such age, except that such ages and elements may be aggregated into a single category of age 90 or
# older.
# Telephone number.
# Fax number.
# Email address.
# Social Security number.
# Social Security number.
# Account number.
# Certificate/license number.
# Vehicle identifiers, serial numbers, or license plate numbers.
# Web URLs.
# IP address.
# Biometric identifiers such as fingerprints or voice prints.
# Full-face photos.
# Any other unique identifying numbers, characteristics, or codes.


class TextChoices(models.TextChoices):
    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return

        for item in cls:
            if value.lower() in (item.name.lower(),
                                 item.label.lower(),
                                 item.value.lower(),
                                 item.name.lower().replace('_', '-'),
                                 item.label.lower().replace('_', '-'),
                                 item.value.lower().replace('_', '-')):
                return item


class UploadedFile(models.Model):
    FileFormats = biospecdb.util.FileFormats
    UPLOAD_DIR = "raw_data/"  # MEDIA_ROOT/raw_data

    meta_data_file = models.FileField(upload_to=UPLOAD_DIR,
                                      validators=[FileExtensionValidator(biospecdb.util.FileFormats.choices())],
                                      help_text="File containing rows of all patient, symptom, and other meta data.")
    spectral_data_file = models.FileField(upload_to=UPLOAD_DIR,
                                          validators=[FileExtensionValidator(biospecdb.util.FileFormats.choices())],
                                          help_text="File containing rows of spectral intensities for the corresponding"
                                                    " meta data file.")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @transaction.atomic
    def clean(self):
        """ Model validation. """
        if hasattr(super, "clean"):
            super.clean()

        # Note: When accessing ``models.FileField`` Django returns ``models.FieldFile`` as a proxy.
        save_data_to_db(self.meta_data_file.file.temporary_file_path(),
                        self.spectral_data_file.file.temporary_file_path())


class Patient(models.Model):
    """ Model an individual patient. """
    MIN_AGE = 0
    MAX_AGE = 150  # NOTE: HIPAA requires a max age of 90 to be stored. However, this is GDPR data so... :shrug:

    class Gender(TextChoices):
        MALE = ("M", _("Male"))  # NOTE: Here variation here act as aliases for bulk column ingestion.
        FEMALE = ("F", _("Female"))  # NOTE: Here variation here act as aliases for bulk column ingestion.

    patient_id = models.UUIDField(unique=True, primary_key=True, default=uuid.uuid4, editable=False)
    gender = models.CharField(max_length=8, choices=Gender.choices, null=True, verbose_name="Gender (M/F)")

    def __str__(self):
        return str(self.patient_id)

    def short_id(self):
        return str(self.patient_id)[:8]


class Visit(models.Model):
    """ Model a patient's visitation to collect health data and biological samples.  """

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visit")

    # NOTE: This has to allow for blank to accommodate the initial vist for which there is no prior.
    previous_visit = models.ForeignKey("self", default=None, blank=True, null=True, on_delete=models.SET_NULL,
                                       related_name="next_visit")

    patient_age = models.IntegerField(validators=[MinValueValidator(Patient.MIN_AGE),
                                                  MaxValueValidator(Patient.MAX_AGE)],
                                      verbose_name="Age")

    def clean(self):
        """ Model validation. """
        if hasattr(super, "clean"):
            super.clean()



        # Validate visits belong to same patient.
        if self.previous_visit is not None and (self.previous_visit.patient_id != self.patient_id):
            raise ValidationError(_("Previous visits do not belong to this patient!"), code="invalid")

        # Validate visits are entered ordered by age.
        if self.previous_visit is not None and (self.patient_age < self.previous_visit.patient_age):
            raise ValidationError(_("Previous visit must NOT be older than this one: patient age before %(prior_age)i "
                                    " > %(current_age)i"),
                                  params={"current_age": self.patient_age,
                                          "prior_age": self.previous_visit.patient_age},
                                  code="invalid")

    def count_prior_visits(self):
        return 0 if self.previous_visit is None else 1 + self.previous_visit.count_prior_visits()

    @property
    def visit_number(self):
        return 1 + self.count_prior_visits()

    def __str__(self):
        return f"patient:{self.patient.short_id()}_visit:{self.visit_number}"


class Disease(models.Model):
    """ Model an individual disease, symptom, or health condition. A patient's instance are stored as models.Symptom"""

    class Types(TextChoices):
        BOOL = auto()
        STR = auto()
        INT = auto()
        FLOAT = auto()

        def cast(self, value):
            if self.name == "BOOL":
                return bool(value)
            elif self.name == "STR":
                return str(value)
            elif self.name == "INT":
                return int(value)
            elif self.name == "FLOAT":
                return float(value)
            else:
                raise NotImplementedError

    name = models.CharField(max_length=128)
    description = models.CharField(max_length=256)
    alias = models.CharField(max_length=128, blank=True,
                             help_text="Alias column name for bulk data ingestion from .csv, etc.")

    # This represents the type/class for Symptom.disease_value.
    # NOTE: For bool types, Symptom.is_symptomatic may suffice.
    value_class = models.CharField(max_length=128, default='', blank=True, null=True, choices=Types.choices)

    def __str__(self):
        return self.name

    def clean(self):
        if hasattr(super, "clean"):
            super.clean()

        if not self.alias:
            self.alias = self.name.replace('_', ' ')


class Symptom(models.Model):
    """ A patient's instance of models.Disease. """
    MIN_SEVERITY = 0
    MAX_SEVERITY = 10

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="symptom")
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name="symptom")

    was_asked = models.BooleanField(default=True)  # Whether the patient was asked whether they have this symptom.
    is_symptomatic = models.BooleanField(default=True)
    days_symptomatic = models.IntegerField(default=None, blank=True, null=True,
                                           validators=[MinValueValidator(0)])
    severity = models.IntegerField(default=None, validators=[MinValueValidator(MIN_SEVERITY),
                                                             MaxValueValidator(MAX_SEVERITY)],
                                   blank=True, null=True)

    # Str format for actual type/class spec'd by Disease.value_class.
    disease_value = models.CharField(blank=True, null=True, max_length=128)

    def clean(self):
        """ Model validation. """
        if hasattr(super, "clean"):
            super.clean()

        if self.disease_value and not self.disease.value_class:
            raise ValidationError(_("The field 'disease_value' is not permitted when `Disease` has no"
                                    "`field:value_class` type specified."),
                                  code="invalid")

        if self.days_symptomatic and self.visit.patient_age and (self.days_symptomatic >
                                                                 (self.visit.patient_age * 365)):
            raise ValidationError(_("The field `days_symptomatic` can't be greater than the patients age (in days):"
                                    " %(days_symptomatic)i > %(age)i"),
                                  params={"days_symptomatic": self.days_symptomatic,
                                          "age": self.visit.patient_age * 365},
                                  code="invalid")

    def __str__(self):
        return f"patient:{self.visit.patient.short_id()}_{self.disease.name}"


class Instrument(models.Model):
    """ Model the instrument/device used to measure spectral data (not the collection of the bio sample). """

    class Spectrometers(TextChoices):
        AGILENT_CORY_630 = auto()

    class SpectrometerCrystal(TextChoices):
        ZNSE = auto()

    spectrometer = models.CharField(default=Spectrometers.AGILENT_CORY_630,
                                    max_length=128,
                                    choices=Spectrometers.choices,
                                    verbose_name="Spectrometer")
    atr_crystal = models.CharField(default=SpectrometerCrystal.ZNSE,
                                   max_length=128,
                                   choices=SpectrometerCrystal.choices,
                                   verbose_name="ATR Crystal")

    def __str__(self):
        return self.spectrometer


class BioSample(models.Model):
    """ Model biological sample and collection method. """
    class SampleKind(TextChoices):
        PHARYNGEAL_SWAB = auto()

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="bio_sample")

    # Sample meta.
    sample_type = models.CharField(default=SampleKind.PHARYNGEAL_SWAB, max_length=128, choices=SampleKind.choices,
                                   verbose_name="Sample Type")
    sample_processing = models.CharField(default="None",
                                         blank=True,
                                         null=True,
                                         max_length=128,
                                         verbose_name="Sample Processing")
    freezing_temp = models.FloatField(blank=True, null=True, verbose_name="Freezing Temperature")
    thawing_time = models.IntegerField(blank=True, null=True, verbose_name="Thawing time")

    def __str__(self):
        return f"{self.visit}_type:{self.sample_type}_pk{self.pk}"  # NOTE: str(self.visit) contains patient ID.


class SpectralData(models.Model):
    """ Model spectral data measured by spectrometer instrument. """

    UPLOAD_DIR = "spectral_data/"  # MEDIA_ROOT/spectral_data

    class SpectralMeasurementKind(TextChoices):
        ATR_FTIR = auto()

    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="spectral_data")
    bio_sample = models.ForeignKey(BioSample, on_delete=models.CASCADE, related_name="spectral_data")

    # Spectrometer meta.
    spectra_measurement = models.CharField(default=SpectralMeasurementKind.ATR_FTIR,
                                           max_length=128,
                                           choices=SpectralMeasurementKind.choices,
                                           verbose_name="Spectra Measurement")
    acquisition_time = models.IntegerField(blank=True, null=True, verbose_name="Acquisition time [s]")

    # TODO: What is this? Could this belong to Instrument?
    n_coadditions = models.IntegerField(default=32, verbose_name="Number of coadditions")

    resolution = models.IntegerField(blank=True, null=True, verbose_name="Resolution [cm-1]")

    # Spectral data.
    # TODO: We could write a custom storage class to write these all to a parquet table instead of individual files.
    # See https://docs.djangoproject.com/en/4.2/howto/custom-file-storage/
    data = models.FileField(upload_to=UPLOAD_DIR,
                            validators=[FileExtensionValidator(UploadedFile.FileFormats.choices())])

    def __str__(self):
        return f"{self.bio_sample.visit}_pk{self.pk}"

    def clean(self):
        """ Model validation. """
        if hasattr(super, "clean"):
            super.clean()

        # Compute QC metrics.
        # TODO: Even with the QC model being its own thing rather than fields here, we may still want to run here
        # such that new data is complete such that it has associated QC metrics.
        ...


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
