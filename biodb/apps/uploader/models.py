from copy import deepcopy
from enum import auto
from pathlib import Path
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
import pandas as pd

from biodb.util import get_field_value, get_object_or_raise_validation, is_valid_uuid, lower, to_uuid
from biodb.qc.qcfilter import QcFilter
import uploader.io
from uploader.loaddata import save_data_to_db
from uploader.sql import secure_name
from uploader.base_models import DatedModel, ModelWithViewDependency, SqlView, TextChoices, Types
from user.models import BaseCenter as UserBaseCenter

# Changes here need to be migrated, committed, and activated.
# See https://docs.djangoproject.com/en/4.2/intro/tutorial02/#activating-models
# python manage.py makemigrations uploader
# git add biodb/apps/uploader/migrations
# git commit -asm"Update uploader model(s)"
# python manage.py migrate --database=bsr

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


class Center(UserBaseCenter):
    @property
    def replica_model(self):
        from user.models import Center as UserCenter
        return UserCenter

    @property
    def replica_db(self):
        return "default"


@receiver(post_delete, sender=Center)
def center_deletion_handler(sender, **kwargs):
    kwargs["instance"].delete_replica()


class UploadedFile(DatedModel):
    """ Model for ingesting bulk data uploads of both array data and meta data files.

        Attributes:
            meta_data_file (:obj:`django.models.FileField`): The uploaded file containing rows of patient meta-data,
                e.g., observations, biosample collection info, etc.
            array_data_file (:obj:`django.models.FileField`): The uploaded file containing rows of patient array
                data.
            center (:obj:`django.models.ForeignKey` of :obj:`user.models.Center`): The center that all new uploaded
                patients will be associated to.
    """

    class Meta:
        db_table = "bulk_upload"
        verbose_name = "Bulk Data Upload"
        get_latest_by = "updated_at"

    FileFormats = uploader.io.FileFormats
    UPLOAD_DIR = "raw_data/"  # MEDIA_ROOT/raw_data

    meta_data_file = models.FileField(upload_to=UPLOAD_DIR,
                                      validators=[FileExtensionValidator(uploader.io.FileFormats.choices())],
                                      help_text="File containing rows of all patient, observation, and other meta"
                                                " data.")
    array_data_file = models.FileField(upload_to=UPLOAD_DIR,
                                       validators=[FileExtensionValidator(uploader.io.FileFormats.choices())],
                                       help_text="File containing rows of array data for the corresponding"
                                                 " meta data file.")
    center = models.ForeignKey(Center, null=False, blank=False, on_delete=models.PROTECT)

    @staticmethod
    def validate_lengths(meta_data, spec_data):
        """ Validate that files must be of equal length (same number of rows). """
        if len(meta_data) != len(spec_data):
            raise ValidationError(_("meta and array data must be of equal length (%(a)i!=%(b)i)."),
                                  params={"a": len(meta_data), "b": len(spec_data)},
                                  code="invalid")

    @staticmethod
    def join_with_validation(meta_data, spec_data):
        """ Validate primary keys are unique and associative. """
        if not meta_data.index.equals(spec_data.index):
            raise ValidationError(_("Patient index mismatch. indexes from %(a)s must exactly match all those from %(b)s"),
                                  params=dict(a=UploadedFile.meta_data_file.field.name,
                                              b=UploadedFile.array_data_file.field.name),
                                  code="invalid")

        try:
            # The simplest way to do this is to utilize pandas.DataFrame.join().
            return meta_data.join(spec_data, how="left", validate="1:1")  # Might as well return the join.
        except pd.errors.MergeError as error:
            raise ValidationError(_("meta and array data must have unique and identical patient identifiers")) from error

    def _validate_and_save_data_to_db(self, dry_run=False):
        try:
            # Read in all data.
            # Note: When accessing ``models.FileField`` Django returns ``models.FieldFile`` as a proxy.
            meta_data = uploader.io.read_meta_data(self.meta_data_file.file,
                                                   index_column=settings.BULK_UPLOAD_INDEX_COLUMN_NAME)
            array_data = uploader.io.read_array_data_table(self.array_data_file.file,
                                                              index_column=settings.BULK_UPLOAD_INDEX_COLUMN_NAME)
            # Validate.
            UploadedFile.validate_lengths(meta_data, array_data)
            # This uses a join so returns the joined data so that it doesn't go to waste if needed, which it is here.
            joined_data = UploadedFile.join_with_validation(meta_data, array_data)

            # Ingest into DB.
            save_data_to_db(None, None, center=self.center, joined_data=joined_data, dry_run=dry_run)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError("An error occurred, check the file content is correct.")

    def clean(self):
        """ Model validation. """
        super().clean()
        self._validate_and_save_data_to_db(dry_run=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._validate_and_save_data_to_db(dry_run=False)

    def asave(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, *args, delete_files=True, **kwargs):
        count, deleted = super().delete(*args, **kwargs)
        if count == 1:
            if delete_files:
                self.meta_data_file.storage.delete(self.meta_data_file.name)
                self.array_data_file.storage.delete(self.array_data_file.name)
        return count, deleted

    def adelete(self, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_orphan_files(cls):
        storage = cls.meta_data_file.field.storage
        path = Path(settings.MEDIA_ROOT) / cls.UPLOAD_DIR
        # Collect all stored media files.
        try:
            fs_files = set([str(path / x) for x in storage.listdir(str(path))[1]])
        except FileNotFoundError:
            return storage, {}
        # Collect all media files referenced in the DB.
        meta_data_files = set(x.meta_data_file.name for x in cls.objects.all())
        array_data_files = set(x.array_data_file.name for x in cls.objects.all())
        # Compute orphaned file list.
        orphaned_files = fs_files - (meta_data_files | array_data_files)
        return storage, orphaned_files


class Patient(DatedModel):
    """ Model an individual patient.

        Attributes:
            patient_id (:obj:`django.models.UUIDField`): Database primary key for patient entry. Autogenerated if
                not provided.
            patient_cid (:obj:`django.models.UUIDField`, optional): Patient identifier provided by associated center.
            center (:obj:`django.models.ForeignKey` of :obj:`user.models.Center`): Center patient belongs to. Only
                users belonging to this center will be able to view this patient.
    """
    MIN_AGE = 0
    MAX_AGE = 150  # NOTE: HIPAA requires a max age of 90 to be stored. However, this is GDPR data so... :shrug:

    class Meta:
        db_table = "patient"
        unique_together = [["patient_cid", "center"]]
        get_latest_by = "updated_at"

    patient_id = models.UUIDField(unique=True,
                                  primary_key=True,
                                  default=uuid.uuid4,
                                  verbose_name="Patient ID")
    patient_cid = models.UUIDField(null=True,
                                   blank=True,
                                   help_text="Patient ID prescribed by the associated center")
    center = models.ForeignKey(Center, null=False, blank=False, on_delete=models.PROTECT)

    @classmethod
    def parse_fields_from_pandas_series(cls, series):
        """ Parse the pandas series for field values returning a dict. """
        return {}

    def __str__(self):
        if self.patient_cid:
            return str(f"PCID:{self.patient_cid}")
        else:
            return str(f"PID:{self.patient_id}")

    def short_id(self):
        if self.patient_cid:
            return str(f"PCID:{str(self.patient_cid)[:8]}")
        else:
            return str(f"PID:{str(self.patient_id)[:8]}")

    def clean(self):
        super().clean()

        # Since patient_cid is only unique with the center, it cannot be the same as patient_id (Patient.pk) since that
        # is unique by itself and would thus prevent duplicate patient_cids across multiple centers.
        if is_valid_uuid(self.patient_cid) and (to_uuid(self.patient_cid) == self.patient_id):
            raise ValidationError(_("Patient ID and patient CID cannot be the same"))


class Visit(DatedModel):
    """ Model a patient's visitation to collect health data and biological data.

        Attributes:
            patient (:obj:`django.models.ForeignKey` of :obj:`Patient`): The patient that this visit belongs to.
            previous_visit (:obj:`django.models.ForeignKey` of :obj:`self`, optional): This can be used to reference
                another ``Visit`` to give order to visitations when collecting dates may not be compliant.
            days_observed (:obj:`django.models.IntegerField`, optional): The number of days that observations have been
                observed for. This applies to all observations related to this visit.
    """

    class Meta:
        db_table = "visit"
        get_latest_by = "updated_at"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visit")

    # NOTE: This has to allow for blank to accommodate the initial vist for which there is no prior.
    previous_visit = models.ForeignKey("self", default=None, blank=True, null=True, on_delete=models.SET_NULL,
                                       related_name="next_visit")

    days_observed = models.IntegerField(default=None,
                                        blank=True,
                                        null=True,
                                        validators=[MinValueValidator(0)],
                                        verbose_name="Days observed",
                                        help_text="Applies to all visit observations unless otherwise specified")

    @classmethod
    def parse_fields_from_pandas_series(cls, series):
        """ Parse the pandas series for field values returning a dict. """
        return dict(days_observed=get_field_value(series, cls, "days_observed"))

    def clean(self):
        """ Model validation. """
        super().clean()

        # Note: Since previous_visit is a foreign key with itself, self.previous_visit is None when blank and doesn't
        # require the ``hasattr(self, previous_visit)`` pattern check that other relations require.
        if settings.AUTO_FIND_PREVIOUS_VISIT and not self.previous_visit:
            last_visit, duplicates_exist = self.auto_find_previous_visit()
            if duplicates_exist:
                raise ValidationError(_("Auto previous visit ambiguity: multiple visits have the exact same"
                                        "'created_at' timestamp - '%(timestamp)s'"),
                                      params={"timestamp": last_visit.created_at})
            self.previous_visit = last_visit

        # Validate that previous visit isn't this visit.
        if self.previous_visit is not None and (self.previous_visit.pk == self.pk):
            raise ValidationError(_("Previous visit cannot not be this current visit"))

        # Validate visits belong to same patient.
        if self.previous_visit is not None and (self.previous_visit.patient_id != self.patient_id):
            raise ValidationError(_("Previous visits do not belong to this patient!"), code="invalid")

        # Validate visits are entered ordered by age.
        if self.previous_visit is not None:
            try:
                patient_age = int(self.observation.get(observable__name="patient_age").observable_value)
            except (Observation.DoesNotExist, ValueError):
                # Note: ``ValueError`` accounts for ``self.observation`` when self.pk hasn't yet been set, since objs
                # are cleaned before saving and the DB populates the pk. Relationships and their traversal aren't
                # possible for objs without primary keys.
                pass
            else:
                try:
                    previous_visit_patient_age = int(self.previous_visit.observation.get(
                        observable__name="patient_age").observable_value)
                except Observation.DoesNotExist:
                    pass
                else:
                    if patient_age < previous_visit_patient_age:
                        raise ValidationError(_("Previous visit must NOT be older than this one: patient age before"
                                                "%(prior_age)i > %(current_age)i"),
                                              params={"current_age": patient_age,
                                                      "prior_age": previous_visit_patient_age},
                                              code="invalid")

    def auto_find_previous_visit(self):
        """ Find the previous visit.

            This is defined as the last visit with a ``created_at`` timestamp less than that of ``self.created_at``.
            WARNING! This may give incorrect results.
        """

        # New visits will not yet have a ``created_at`` entry as that happens upon save to the DB. In this case,
        # we could assume that save() is imminent and use the current time, i.e., ``datatime.datetime.now()``. However,
        # this seems sketchy, instead, it's safer to just not filter by creation timestamp since everything present
        # was added in the past. Note: Django fixture data could have future timestamps but that would be a curator bug.
        if self.created_at:
            previous_visits = Visit.objects.filter(patient_id=self.patient_id,
                                                   created_at__lt=self.created_at).order_by('created_at')
        else:
            previous_visits = Visit.objects.filter(patient_id=self.patient_id).order_by('created_at')

        if not previous_visits:
            return None, False

        last_visit = previous_visits.last()

        if last_visit == self:
            # This could be true when updating the only existing visit for a given patient, however, the above
            # filter(created_at__lt=self.created_at) would prevent this and shouldn't be possible otherwise. That being
            # said, we might as well make this more robust, just in case.
            return None, False

        # Is last visit unique?
        # TODO: Disambiguate using age and/or pk, and/or something else?
        duplicates_exist = previous_visits.filter(created_at=last_visit.created_at).count() > 1

        return last_visit, duplicates_exist

    def count_prior_visits(self):
        return 0 if self.previous_visit is None else 1 + self.previous_visit.count_prior_visits()

    @property
    def visit_number(self):
        return 1 + self.count_prior_visits()

    @property
    def center(self):
        return self.patient.center

    def __str__(self):
        return f"patient:{self.patient}_visit:{self.visit_number}"


def validate_import(value):
    """ Validate that ``value`` (fully-quilified-name) can be imported. """
    try:
        import_string(value)
    except ImportError:
        raise ValidationError(_("'%(a)s' cannot be imported. Server re-deployment may be required."
                                " Please reach out to the server admin."),
                              params=dict(a=value),
                              code="invalid")


class Observable(ModelWithViewDependency):
    """ Model an individual observable, observation, or health condition.
        A patient's instances of this are stored as models.Observation.

        Attributes:
            category (:obj:`django.models.CharField`): Observable category selected from: BLOODWORK, COMORBIDITY, DRUG,
                PATIENT_INFO, PATIENT_INFO_II, PATIENT_PREP, SYMPTOM, TEST, VITALS.
            name (:obj:`django.models.CharField`): Name of observable, e.g., age, gender, fever, diabetes, etc.
            description (:obj:`django.models.CharField`): Verbose description of observable semantics.
            alias (:obj:`django.models.CharField`): Alias column name for bulk data ingestion from .csv, etc.
            value_class (:obj:`django.models.CharField`): Value type selected from: BOOL, INT, STR, FLOAT.
            value_choices (:obj:`django.models.CharField`, optional): Supply comma separated text choices for STR value_classes
                e.g., 'LOW, MEDIUM, HIGH'.
            validator (:obj:`django.models.CharField`, optional): This must be the fully qualified Python name e.g.,
                'django.core.validators.validate_email'.
            center (:obj:`django.models.ManyToManyField` of :obj:`user.models.Center`): Only visible to users of these
                centers. Selecting none is equivalent to all. When None, blank inline observations of this observable
                will be automatically added to data input forms.
    """

    class Category(TextChoices):
        BLOODWORK = auto()
        COMORBIDITY = auto()
        DRUG = auto()
        PATIENT_INFO = auto()
        PATIENT_INFO_II = auto()
        PATIENT_PREP = auto()
        SYMPTOM = auto()
        TEST = auto()
        VITALS = auto()

    Types = Types

    sql_view_dependencies = ("uploader.models.FullPatientView",)

    class Meta:
        db_table = "observable"
        get_latest_by = "updated_at"
        constraints = [models.UniqueConstraint(Lower("name"),
                                               name="unique_observable_name"),
                       models.UniqueConstraint(Lower("alias"),
                                               name="unique_alias_name")]

    category = models.CharField(max_length=128, null=False, blank=False, choices=Category.choices)

    # NOTE: See above constraint for case-insensitive uniqueness.
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=256)

    # NOTE: See meta class constraint for case-insensitive uniqueness.
    alias = models.CharField(max_length=128,
                             help_text="Alias column name for bulk data ingestion from .csv, etc.")

    # This represents the type/class for Observation.observable_value.
    value_class = models.CharField(max_length=128, default=Types.BOOL, choices=Types.choices)
    value_choices = models.CharField(max_length=512,
                                     blank=True,
                                     null=True,
                                     help_text="Supply comma separated text choices for STR value_classes."
                                               " E.g., 'LOW, MEDIUM, HIGH'")
    validator = models.CharField(max_length=128,
                                 blank=True,
                                 null=True,
                                 help_text="This must be the fully qualified Python name."
                                           " E.g., 'django.core.validators.validate_email'.",
                                 validators=[validate_import])

    # An observable without a center is generic and accessible by any and all centers.
    center = models.ManyToManyField(Center,
                                    blank=True,
                                    related_name="observable",
                                    help_text="Only visible to users of these centers.\n"
                                              "Selecting none is equivalent to all. When None, blank inline "
                                              "observations of this observable will be automatically added to data "
                                              "input forms.")

    # default = models.ManyToManyField(Center,
    #                                  blank=True,
    #                                  related_name="observable_default",
    #                                  help_text="Automatically add an observation of this observable to the data input"
    #                                            " form for users of these centers.\n"
    #                                            "Selecting none is equivalent to all.")

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if not self.alias:
            self.alias = self.name.replace('_', ' ')

        if self.value_choices and (Observable.Types(self.value_class) is not Observable.Types.STR):
            raise ValidationError(_("Observable choices are only permitted of STR value_class, not '%(a)s'."),
                                  params=dict(a=self.value_class))

    @staticmethod
    def list_choices(choices):
        """ Convert a csv string of choices to a list. """
        if choices:
            return [x.strip().upper() for x in choices.split(',')]

    @staticmethod
    def djangofy_choices(choices):
        """ Convert a csv string of choices to that needed by Django. """
        if choices:
            return [(x, x) for x in Observable.list_choices(choices)]


class Observation(DatedModel):
    """ A patient's instance of a single observable.

        Attributes:
            visit (:obj:`django.models.ForeignKey` of :obj:`Visit`): The visit that this observation belongs to.
            observable (:obj:`django.models.ForeignKey` of :obj:`Observable`): The observable that this is an
                observation of.
            days_observed (:obj:`django.models.CharField`, optional): The number of days that this observation has been
                observed for.
            observable_value (:obj:`django.models.CharField`): The actual value that is the observation. E.g., True,
                97.8, etc.
    """

    class Meta:
        db_table = "observation"
        get_latest_by = "updated_at"

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="observation")
    observable = models.ForeignKey(Observable, on_delete=models.CASCADE, related_name="observation")

    days_observed = models.IntegerField(default=None,
                                        blank=True,
                                        null=True,
                                        validators=[MinValueValidator(0)],
                                        verbose_name="Days observed",
                                        help_text="Supersedes Visit.days_observed")

    # Str format for actual type/class spec'd by Observable.value_class.
    observable_value = models.CharField(blank=True,
                                        null=True,
                                        default='',
                                        max_length=128)

    def clean(self):
        """ Model validation. """
        super().clean()

        if hasattr(self, "observable"):
            # Note: global observables have no observable.center.
            if self.observable.center.count() and (self.visit.patient.center not in self.observable.center.all()):
                # Note: Don't expose centers here.
                raise ValidationError(_("Patient observation.observable must belong to patient's center."))

            # Check that value is castable by casting.
            # NOTE: ``observable_value`` is a ``CharField`` so this will get cast back to a str again, and it could be
            # argued that there's no point in storing the cast value... but :shrug:.
            try:
                self.observable_value = Observable.Types(self.observable.value_class).cast(self.observable_value)
            except ValueError:
                raise ValidationError(_("The value '%(value)s' can not be cast to the expected type of '%(type)s' for"
                                        " '%(observable_name)s'"),
                                      params={"observable_name": self.observable.name,
                                              "type": self.observable.value_class,
                                              "value": self.observable_value},
                                      code="invalid")

            if choices := self.observable.value_choices:
                if (value := str(self.observable_value).strip().upper()) not in Observable.list_choices(choices):
                    raise ValidationError(_("Value must be one of '%(a)s', not '%(b)s'"),
                                          params=dict(a=choices, b=value))

            if self.observable.validator:
                func = import_string(self.observable.validator)
                func(self.observable_value)

    @property
    def center(self):
        return self.visit.patient.center

    def __str__(self):
        return f"patient:{self.visit.patient.short_id()}_{self.observable.name}"


class Instrument(DatedModel):
    """ Model the instrument/device used to measure array data.

        Note: This is not the collection method of the bio sample but the device used to analyze the
        biosample.

        Attributes:
            id (:obj:`django.models.UUIDField`): Database primary key for instrument. Autogenerated if not provided.
            cid (:obj:`django.models.CharField`): The instrument ID provided by the center.
            manufacturer (:obj:`django.models.CharField`): Instrument manufacturer name.
            model (:obj:`django.models.CharField`): Instrument model name.
            serial_number (:obj:`django.models.CharField`): Instrument serial number (SN#).
            center (:obj:`django.models.ForeignKey` of :obj:`user.models.Center`, optional): The center that this
                instrument belongs to. If ``null`` this instrument belongs to all centers, e.g., one used at a central
                processing lab.
    """

    class Meta:
        db_table = "instrument"
        get_latest_by = "updated_at"

    # Instrument.
    id = models.UUIDField(unique=True, primary_key=True, default=uuid.uuid4, verbose_name="instrument id")
    cid = models.CharField(max_length=128, verbose_name="instrument cid")
    manufacturer = models.CharField(max_length=128, verbose_name="Instrument manufacturer")
    model = models.CharField(max_length=128, verbose_name="Instrument model")
    serial_number = models.CharField(max_length=128, verbose_name="Instrument SN#")

    center = models.ForeignKey(Center, null=True, blank=True, on_delete=models.PROTECT)

    @classmethod
    def parse_fields_from_pandas_series(cls, series):
        """ Parse the pandas series for field values returning a dict. """
        return {}

    def __str__(self):
        return f"{self.manufacturer}_{self.model}_{self.id}"


class BioSampleType(DatedModel):
    """ The type of biosample collected.

        Attributes:
            name (:obj:`django.models.CharField`): The type name, e.g., nasal swab, pharyngeal swab, urine, etc.
    """
    class Meta:
        db_table = "bio_sample_type"
        get_latest_by = "updated_at"

    name = models.CharField(max_length=128, verbose_name="Sample Type")

    def __str__(self):
        return self.name


class BioSample(DatedModel):
    """ Model biological sample and collection method.

        Attributes:
            visit (:obj:`django.models.ForeignKey` of :obj:`Visit`): The visit that this sample belongs to.
            sample_cid (:obj:`django.models.CharField`, optional): Sample ID provided by center responsible for sample
                collection.
            sample_study_id (:obj:`django.models.CharField`, optional): Sample study ID.
            sample_study_name (:obj:`django.models.CharField`, optional): Sample study name.
            sample_type (:obj:`django.models.ForeignKey` of :obj:`BioSampleType`): The type of biosample e.g., nasal
                swab, pharyngeal swab, urine, etc.
            sample_processing (:obj:`django.models.CharField`, optional): Sample processing description.
            sample_extraction (:obj:`django.models.CharField`, optional): Sample extraction description.
            sample_extraction_tube (:obj:`django.models.CharField`, optional): Sample extraction tube brand name.
            centrifuge_time (:obj:`django.models.IntegerField`, optional): Extraction tube centrifuge time [seconds].
            centrifuge_rpm (:obj:`django.models.IntegerField`, optional): Extraction tube centrifuge RPM.
            freezing_temp (:obj:`django.models.FloatField`, optional): Freezing temperature [C].
            thawing_temp (:obj:`django.models.FloatField`, optional): Thawing temperature [C].
            thawing_time (:obj:`django.models.FloatField`, optional): Thawing time [minutes].
            freezing_time (:obj:`django.models.FloatField`, optional): Freezing time [days].
    """

    class Meta:
        db_table = "bio_sample"
        get_latest_by = "updated_at"

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="bio_sample")

    # Sample meta.
    sample_cid = models.CharField(blank=True,
                                  null=True,
                                  max_length=256,
                                  verbose_name="Sample CID")
    sample_study_id = models.CharField(blank=True,
                                       null=True,
                                       max_length=256,
                                       verbose_name="Sample Study ID")
    sample_study_name = models.CharField(blank=True,
                                         null=True,
                                         max_length=256,
                                         verbose_name="Sample Study Name")
    sample_type = models.ForeignKey(BioSampleType,
                                    on_delete=models.CASCADE,
                                    related_name="bio_sample",
                                    verbose_name="Sample Type")
    sample_processing = models.CharField(blank=True,
                                         null=True,
                                         max_length=128,
                                         verbose_name="Sample Processing Description")
    sample_extraction = models.CharField(blank=True,
                                         null=True,
                                         max_length=128,
                                         verbose_name="Sample Extraction Description")
    sample_extraction_tube = models.CharField(blank=True,
                                              null=True,
                                              max_length=128,
                                              verbose_name="Sample Extraction Tube Brand Name")
    centrifuge_time = models.IntegerField(blank=True, null=True, verbose_name="Extraction Tube Centrifuge Time [s]")
    centrifuge_rpm = models.IntegerField(blank=True, null=True, verbose_name="Extraction Tube Centrifuge RPM")
    freezing_temp = models.FloatField(blank=True, null=True, verbose_name="Freezing Temperature [C]")
    thawing_temp = models.FloatField(blank=True, null=True, verbose_name="Thawing Temperature [C]")
    thawing_time = models.FloatField(blank=True, null=True, verbose_name="Thawing time [minutes]")
    freezing_time = models.FloatField(blank=True, null=True, verbose_name="Freezing time [days]")

    @classmethod
    def parse_fields_from_pandas_series(cls, series):
        """ Parse the pandas series for field values returning a dict. """
        sample_type = lower(get_field_value(series, cls, "sample_type"))
        sample_type = get_object_or_raise_validation(BioSampleType, name=sample_type)
        return dict(sample_type=sample_type,
                    sample_cid=get_field_value(series, cls, "sample_cid"),
                    sample_study_id=get_field_value(series, cls, "sample_study_id"),
                    sample_study_name=get_field_value(series, cls, "sample_study_name"),
                    sample_processing=get_field_value(series, cls, "sample_processing"),
                    sample_extraction=get_field_value(series, cls, "sample_extraction"),
                    sample_extraction_tube=get_field_value(series, cls, "sample_extraction_tube"),
                    centrifuge_time=get_field_value(series, cls, "centrifuge_time"),
                    centrifuge_rpm=get_field_value(series, cls, "centrifuge_rpm"),
                    freezing_temp=get_field_value(series, cls, "freezing_temp"),
                    freezing_time=get_field_value(series, cls, "freezing_time"),
                    thawing_time=get_field_value(series, cls, "thawing_time"),
                    thawing_temp=get_field_value(series, cls, "thawing_temp"))

    @property
    def center(self):
        return self.visit.patient.center

    def __str__(self):
        return f"{self.visit}_type:{self.sample_type}_pk{self.pk}"  # NOTE: str(self.visit) contains patient ID.


class ArrayMeasurementType(DatedModel):
    """ Array measurement type.

        Attributes:
            name (:obj:`django.models.CharField`): Name of type.
    """

    class Meta:
        db_table = "array_measurement_type"
        get_latest_by = "updated_at"

    name = models.CharField(max_length=128, verbose_name="Array Measurement")

    def __str__(self):
        return self.name


class ArrayData(DatedModel):
    """ Model array data measured by instrument from biosample data.

        Attributes:
            id (:obj:`django.models.UUIDField`): The database primary key for the entry, Autogenerated if not provided.
            data (:obj:`django.models.FileField`): The uploaded file containing the array data.
            instrument (:obj:`django.models.ForeignKey` of :obj:`Instrument`): The instrument used to measure and
                produce the array data.
            bio_sample (:obj:`django.models.CharField` of :obj:`BioSample`): The biosample that was analyzed.
            measurement_type (:obj:`django.models.ForeignKey`  of :obj:`ArrayMeasurementType`): The measurement type.
            measurement_id (:obj:`django.models.CharField`, optional): Identifier string for data.
            acquisition_time (:obj:`django.models.IntegerField`, optional): The acquisition time [s].
            resolution (:obj:`django.models.CharField`, IntegerField): The resolution [1/cm]
            power (:obj:`django.models.FloatField`, optional): Power incident to the sample [mW]
            temperature (:obj:`django.models.FloatField`, optional: Temperature [C].
            pressure (:obj:`django.models.FloatField`, optional): Pressure [bar].
            date (:obj:`django.models.DateTimeField`, optional): Humidity [%].
    """

    class Meta:
        db_table = "array_data"
        verbose_name = "Array Data"
        verbose_name_plural = verbose_name
        get_latest_by = "updated_at"

    UPLOAD_DIR = "array_data/"  # MEDIA_ROOT/array_data

    id = models.UUIDField(unique=True, primary_key=True, default=uuid.uuid4)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="array_data")
    bio_sample = models.ForeignKey(BioSample, on_delete=models.CASCADE, related_name="array_data")

    # Measurement info
    measurement_id = models.CharField(max_length=128, blank=True, null=True)
    measurement_type = models.ForeignKey(ArrayMeasurementType,
                                         on_delete=models.CASCADE,
                                         verbose_name="Measurement type",
                                         related_name="array_data")
    acquisition_time = models.IntegerField(blank=True, null=True, verbose_name="Acquisition time [s]")
    resolution = models.IntegerField(blank=True, null=True, verbose_name="Resolution [1/cm]")
    power = models.FloatField(max_length=128, blank=True, null=True, verbose_name="Power incident to the sample [mW]")
    temperature = models.FloatField(max_length=128, blank=True, null=True, verbose_name="Temperature [C]")
    pressure = models.FloatField(max_length=128, blank=True, null=True, verbose_name="Pressure [bar]")
    humidity = models.FloatField(max_length=128, blank=True, null=True, verbose_name="Humidity [%]")
    date = models.DateTimeField(blank=True, null=True)

    data = models.FileField(upload_to=UPLOAD_DIR,
                            validators=[FileExtensionValidator(UploadedFile.FileFormats.choices())],
                            max_length=256,
                            verbose_name="Array data file")

    @classmethod
    def parse_fields_from_pandas_series(cls, series):
        """ Parse the pandas series for field values returning a dict. """
        measurement_type = lower(get_field_value(series, cls, "measurement_type"))
        measurement_type = get_object_or_raise_validation(ArrayMeasurementType, name=measurement_type)
        return dict(measurement_type=measurement_type,
                    acquisition_time=get_field_value(series, cls, "acquisition_time"),
                    resolution=get_field_value(series, cls, "resolution"),
                    power=get_field_value(series, cls, "power"),
                    temperature=get_field_value(series, cls, "temperature"),
                    pressure=get_field_value(series, cls, "pressure"),
                    humidity=get_field_value(series, cls, "humidity"),
                    date=get_field_value(series, cls, "date"))

    @property
    def center(self):
        return self.bio_sample.visit.patient.center

    def __str__(self):
        return str(self.generate_filename())

    def get_annotators(self):
        """ Return list of all quality control annotators. """
        return list(set([annotation.annotator for annotation in self.qc_annotation.all()]))

    def get_unrun_annotators(self, existing_annotators=None):
        """ Return list of default quality control annotators that have not yet been run against this data. """
        # Get annotators from existing annotations.
        if existing_annotators is None:
            existing_annotators = self.get_annotators()

        # Some default annotators may not have been run yet (newly added), so check.
        all_default_annotators = QCAnnotator.objects.filter(default=True)

        return list(set(all_default_annotators) - set(existing_annotators))

    def get_array_data(self):
        """ Return array data as instance of uploader.io.ArrayData. """
        return uploader.io.array_data_from_json(self.data)

    def generate_filename(self):
        return Path(f"{self.bio_sample.visit.patient.patient_id}_{self.bio_sample.pk}_{self.id}")\
            .with_suffix(uploader.io.FileFormats.JSONL)

    def clean_data_file(self):
        """ Read in data from uploaded file and store as json.

            The schema is equivalent to `json.dumps(dataclasses.asdict(uploader.io.ArrayData))``.
        """

        # Note: self.data is a FieldFile and is never None so check is "empty" instead, i.e., self.data.name is None.
        if not self.data:
            return

        try:
            data = uploader.io.read_array_data(self.data)
        except uploader.io.DataSchemaError as error:
            raise ValidationError(_("%(msg)s"), params={"msg": error})

        # Filenames need to be cleaned, however, don't clean TEMP filenames otherwise they won't be deleted.
        if Path(self.data.name).name.startswith(uploader.io.TEMP_FILENAME_PREFIX):
            filename = self.data.name
        else:
            filename = self.generate_filename()
        json_str = uploader.io.array_data_to_json(file=None, data=data)

        return ContentFile(json_str, name=filename)

    def clean(self):
        # Normalize data file format and clobber the uploaded file with the cleaned one.
        if (cleaned_file := self.clean_data_file()) is not None:
            # Update file.
            self.data = cleaned_file

    #@transaction.atomic(using="bsr")  # Really? Not sure if this even can be if run in background...
    def annotate(self, annotator=None, force=False) -> list:
        """ Run the quality control annotation on the array data. """
        # TODO: This needs to return early and run in the background.

        existing_annotators = self.get_annotators()

        # Run only the provided annotator.
        if annotator:
            if annotator in existing_annotators:
                if not force:
                    return
                annotation = self.qc_annotation.get(annotator=annotator)
            else:
                annotation = QCAnnotation(annotator=annotator, array_data=self)
            return [annotation.run()]

        annotations = []
        # Rerun existing annotations.
        if force and existing_annotators:
            for annotation in self.qc_annotation.all():
                annotations.append(annotation.run())

        new_annotators = self.get_unrun_annotators(existing_annotators=existing_annotators)

        # Create new annotations.
        for annotator in new_annotators:
            annotation = QCAnnotation(annotator=annotator, array_data=self)
            annotations.append(annotation.run())

        return annotations if annotations else None  # Don't ret empty list.

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Compute QC metrics.
        # TODO: Even with the QC model being its own thing rather than fields here, we may still want to run here
        # such that new data is complete such that it has associated QC metrics.
        if settings.AUTO_ANNOTATE:
            # TODO: This should return early and runs async in the background.
            self.annotate()

    def asave(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, *args, delete_files=True, **kwargs):
        count, deleted = super().delete(*args, **kwargs)
        if count == 1:
            if delete_files:
                self.data.storage.delete(self.data.name)
        return count, deleted

    def adelete(self, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_orphan_files(cls):
        storage = cls.data.field.storage
        path = Path(settings.MEDIA_ROOT) / cls.UPLOAD_DIR
        # Collect all stored media files.
        try:
            fs_files = set([str(path / x) for x in storage.listdir(str(path))[1]])
        except FileNotFoundError:
            return storage, {}
        # Collect all media files referenced in the DB.
        data_files = set(x.data.name for x in cls.objects.all())
        # Compute orphaned file list.
        orphaned_files = fs_files - data_files
        return storage, orphaned_files


class ObservationsView(SqlView, models.Model):
    db = "bsr"

    class Meta:
        managed = False
        db_table = "v_observations"

    visit_id = models.BigIntegerField(primary_key=True)
    observation_id = models.ForeignKey(Observation, db_column="observation_id", on_delete=models.DO_NOTHING)
    observable_id = models.ForeignKey(Observable, db_column="observable_id", on_delete=models.DO_NOTHING)
    observable = deepcopy(Observable.name.field)
    observable.name = observable.db_column = "observable"
    value_class = deepcopy(Observable.value_class.field)
    days_observed = deepcopy(Observation.days_observed.field)
    observable_category = deepcopy(Observable.category.field)
    observable_value = deepcopy(Observation.observable_value.field)

    @classmethod
    def sql(cls):
        sql = f"""
        CREATE VIEW {cls._meta.db_table} AS
        SELECT s.visit_id,
               s.id AS observation_id,
               d.id AS observable_id,
               d.name AS observable,
               d.category AS observable_category,
               d.value_class,
               s.days_observed,
               s.observable_value
        FROM observation s
        JOIN observable d ON d.id=s.observable_id
        """  # nosec B608
        return sql, None


class VisitObservationsView(SqlView, models.Model):
    class Meta:
        managed = False
        db_table = "v_visit_observations"

    sql_view_dependencies = (ObservationsView,)
    db = "bsr"

    visit_id = models.BigIntegerField(primary_key=True)

    @classmethod
    def sql(cls):
        observables = Observable.objects.all().order_by("pk")
        view = cls._meta.db_table
        d = []
        for observable in observables:
            if observable.name.lower() in settings.FLAT_VIEW_OBSERVABLE_EXCLUSION_LIST:
                continue
            secure_name(observable.name)
            if observable.value_class == "FLOAT":
                value = 'cast(observable_value AS REAL)'
            elif observable.value_class == "INTEGER":
                value = "cast(observable_value AS INTEGER)"
            else:
                value = "observable_value"
            d.append(f"max(case when observable = '{observable.name}' then {value} else null end) as "
                     f"{observable.name}")

        d = "\n,      ".join(d)

        # NOTE: Params aren't allowed in view statements with sqlite. Since observable can be added to the DB this poses
        # as a risk since someone with access to creating observables could inject into observable.name arbitrary SQL.
        # Calling secure_name(observable.name) may not entirely guard against this even though its intention is to do
        # so.
        sql = f"""
        create view {view} as
        select visit_id
        ,      {d} 
          from v_observations 
         group by visit_id
        """  # nosec B608

        return sql, None


class FullPatientView(SqlView, models.Model):
    class Meta:
        managed = False
        db_table = "flat_view"

    sql_view_dependencies = (VisitObservationsView,)
    db = "bsr"

    @classmethod
    def sql(cls):
        # WARNING: The data exporters and charts rely on the array data column := "data", so we special case this
        # instead of using ``_create_field_str_list``. The charts also rely on the field "patient_id" being present, so
        # that too we special case. Besides, patient.center shouldn't be included and that's the only other field.
        sql = f"""
                create view {cls._meta.db_table} as 
                select p.patient_id,
                       {cls._create_field_str_list("bst", BioSampleType, extra_excluded_field_names=["id"])},
                       {cls._create_field_str_list("bs",
                                                   BioSample,
                                                   extra_excluded_field_names=["id",
                                                                               "sample_cid",
                                                                               "sample_study_name"])},
                       {cls._create_field_str_list("i", Instrument, extra_excluded_field_names=["id", "cid"])},
                       {cls._create_field_str_list("smt", ArrayMeasurementType, extra_excluded_field_names=["id"])},
                       {cls._create_field_str_list("sd",
                                                   ArrayData,
                                                   extra_excluded_field_names=[ArrayData.data.field.name,
                                                                               "id",
                                                                               "measurement_id",
                                                                               "date"])},
                       sd.data,              
                       vs.*
                  from patient p
                  join visit v on p.patient_id=v.patient_id
                  join bio_sample bs on bs.visit_id=v.id
                  join bio_sample_type bst on bst.id=bs.sample_type_id
                  join array_data sd on sd.bio_sample_id=bs.id
                  join array_measurement_type smt on smt.id=sd.measurement_type_id
                  join instrument i on i.id=sd.instrument_id
                  left outer join v_visit_observations vs on vs.visit_id=v.id
                """  # nosec B608
        return sql, None


def validate_qc_annotator_import(value):
    try:
        obj = import_string(value)
    except ImportError:
        raise ValidationError(_("'%(a)s' cannot be imported. Server re-deployment may be required."
                                " Please reach out to the server admin."),
                              params=dict(a=value),
                              code="invalid")

    if obj and not issubclass(obj, QcFilter):  # NOTE: issubclass is used since QcFilter is abstract.
        raise ValidationError(_("fully_qualified_class_name must be of type %(a)s not"
                                "'%(b)s'"),
                              params=dict(a=type(obj), b=QcFilter.__qualname__),
                              code="invalid")


class QCAnnotator(DatedModel):
    """ Quality Control annotator.

        Attributes:
            name (:obj:`django.models.CharField`): The name of the annotator.
            fully_qualified_class_name (:obj:`django.models.CharField`): This must be the fully qualified Python name
                for an implementation of QCFilter, e.g., 'myProject.qc.myQCFilter'.
            value_type (:obj:`django.models.CharField`): Value type selected from: BOOL, STR, INT, FLOAT.
            description (:obj:`django.models.CharField`, optional): A verbose description of the annotator's semantics.
            default (:obj:`django.models.BooleanField`, optional): Specifies whether this annotator is considered a
                "default" or "global" annotator that will can be automatically applied to all array data entries.
    """

    class Meta:
        db_table = "qc_annotator"
        get_latest_by = "updated_at"

    Types = Types

    name = models.CharField(max_length=128, unique=True, blank=False, null=False)
    fully_qualified_class_name = models.CharField(max_length=128,
                                                  blank=False,
                                                  null=False,
                                                  unique=True,
                                                  help_text="This must be the fully qualified Python name for an"
                                                            " implementation of QCFilter, e.g.,"
                                                            "'myProject.qc.myQCFilter'.",
                                                  validators=[validate_qc_annotator_import])
    value_type = models.CharField(blank=False, null=False, max_length=128, default=Types.BOOL, choices=Types.choices)
    description = models.CharField(blank=True, null=True, max_length=256)
    default = models.BooleanField(default=True,
                                  blank=False,
                                  null=False,
                                  help_text="If True it will apply to all array data samples.")

    def __str__(self):
        return f"{self.name}: {self.fully_qualified_class_name}"

    def cast(self, value):
        if value:
            return self.Types(self.value_type).cast(value)

    def run(self, *args, **kwargs):
        obj = import_string(self.fully_qualified_class_name)
        return obj.run(obj, *args, **kwargs)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if settings.RUN_DEFAULT_ANNOTATORS_WHEN_SAVED and self.default:
            # Run annotator on all array data samples.
            for data in ArrayData.objects.all():
                # Since this annotator could have been altered (from django) rather than being new, annotations
                # of this annotator may already exist, thus we need to force them to be re-run.
                data.annotate(annotator=self, force=True)


class QCAnnotation(DatedModel):
    """ A Quality Control annotation of a array data entry.

        Attributes:
            value (:obj:`django.models.CharField`): The actual annotation value/data/result.
            annotator (:obj:`django.models.ForeignKey` of :obj:`QCAnnotator`): The quality control annotator used to
                produce annotate the array data entry.
            array_data (:obj:`django.models.ForeignKey` of :obj:`ArrayData`): The annotated array data entry.
    """

    class Meta:
        db_table = "qc_annotation"
        unique_together = [["annotator", "array_data"]]
        get_latest_by = "updated_at"

    value = models.CharField(blank=True, null=True, max_length=128)

    annotator = models.ForeignKey(QCAnnotator,
                                  blank=False,
                                  null=False,
                                  on_delete=models.CASCADE,
                                  related_name="qc_annotation")
    array_data = models.ForeignKey(ArrayData, on_delete=models.CASCADE, related_name="qc_annotation")

    @property
    def center(self):
        return self.array_data.bio_samaple.visit.patient.center

    def __str__(self):
        return f"{self.annotator.name}: {self.value}"

    def get_value(self):
        if self.annotator:
            return self.annotator.cast(self.value)

    def run(self, save=True):
        value = self.annotator.run(self.array_data)
        self.value = value

        if save:
            self.save()

        return self.value

    def save(self, *args, **kwargs):
        self.run(save=False)
        super().save(*args, **kwargs)

    def asave(self, *args, **kwargs):
        raise NotImplementedError


def get_center(obj):
    if isinstance(obj, Center):
        return obj
    elif isinstance(obj, UserBaseCenter):
        try:
            return Center.objects.get(pk=obj.pk)
        except Center.DoesNotExist:
            return
    elif hasattr(obj, "center"):
        return obj.center
