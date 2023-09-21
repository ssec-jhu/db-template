from django.contrib import admin
from django.core.exceptions import ValidationError
import django.forms as forms

from .models import BioSample, Disease, Instrument, Patient, SpectralData, Symptom, UploadedFile, Visit, QCAnnotator,\
    QCAnnotation


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    list_display = ["spectrometer", "atr_crystal"]
    ordering = ["spectrometer"]


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    search_fields = ["created_at"]
    search_help_text = "Creation timestamp"
    list_display = ["pk", "created_at", "meta_data_file", "spectral_data_file"]
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "created_at"
    ordering = ("-updated_at",)


class QCAnnotationInline(admin.TabularInline):
    model = QCAnnotation
    extra = 1
    show_change_link = True


@admin.register(QCAnnotation)
class QCAnnotationAdmin(admin.ModelAdmin):
    search_fields = ["annotator__name"]
    search_help_text = "Annotator Name"
    readonly_fields = ("value", "created_at", "updated_at")  # TODO: Might need specific user group for timestamps.
    list_display = ["annotator_name", "value", "annotator_value_type"]
    ordering = ("-updated_at",)

    @admin.display
    def annotator_name(self, obj):
        return obj.annotator.name

    @admin.display
    def annotator_value_type(self, obj):
        return obj.annotator.value_type


@admin.register(QCAnnotator)
class QCAnnotatorAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    search_help_text = "Name"
    # TODO: Might need specific user group for timestamps.)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)

    list_display = ["name", "fully_qualified_class_name", "default", "value_type"]


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    search_help_text = "Disease name"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    ordering = ["name"]

    list_display = ["name", "description", "symptom_count"]

    @admin.display
    def symptom_count(self, obj):
        return len(obj.symptom.all())


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    search_fields = ["disease__name"]
    search_help_text = "Disease OR patient ID"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)

    def get_search_results(self, request, queryset, search_term):
        """ search_fields filters with an AND when we need an OR
            See https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.search_fields
        """
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        try:
            queryset |= self.model.objects.filter(visit__patient_id=search_term)
        except ValidationError:
            pass

        return queryset, may_have_duplicates

    list_display = ["patient_id", "disease_name", "days_symptomatic", "severity", "visit"]
    list_editable = ["days_symptomatic", "severity"]

    @admin.display
    def patient_id(self, obj):
        return obj.visit.patient.patient_id

    @admin.display
    def disease_name(self, obj):
        return obj.disease.name


class SymptomInline(admin.TabularInline):
    model = Symptom
    extra = 10
    show_change_link = True


class SpectralDataInline(admin.StackedInline):
    model = SpectralData
    extra = 1
    radio_fields = {"instrument": admin.HORIZONTAL}
    show_change_link = True


@admin.register(SpectralData)
class SpectralDataAdmin(admin.ModelAdmin):
    radio_fields = {"instrument": admin.HORIZONTAL}

    search_fields = ["bio_sample__visit__patient__patient_id"]
    search_help_text = "Patient ID"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "updated_at"
    list_display = ["patient_id", "instrument", "data"]
    inlines = [QCAnnotationInline]
    ordering = ("-updated_at",)

    @admin.display
    def patient_id(self, obj):
        return obj.bio_sample.visit.patient_id


class BioSampleInline(admin.TabularInline):
    model = BioSample
    extra = 1
    show_change_link = True


@admin.register(BioSample)
class BioSampleAdmin(admin.ModelAdmin):
    search_fields = ["sample_type"]
    search_help_text = "Sample type OR patient ID"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)

    def get_search_results(self, request, queryset, search_term):
        """ search_fields filters with an AND when we need an OR
            See https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.search_fields
        """
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        try:
            queryset |= self.model.objects.filter(visit__patient_id=search_term)
        except ValidationError:
            pass

        return queryset, may_have_duplicates

    list_display = ["patient_id", "sample_type"]

    @admin.display
    def patient_id(self, obj):
        return obj.visit.patient_id

    inlines = [SpectralDataInline]


class VisitAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.patient_id:
            self.fields["previous_visit"].queryset = Visit.objects.filter(patient=self.instance.patient_id)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    form = VisitAdminForm
    search_fields = ["patient__patient_id"]
    search_help_text = "Patient ID"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)

    # autocomplete_fields = ["previous_visit"]  # Conflicts with VisitAdminForm queryset.
    inlines = [BioSampleInline, SymptomInline]

    list_display = ["patient_id", "visit_count", "gender", "previous_visit"]

    @admin.display
    def patient_id(self, obj):
        return obj.patient.patient_id

    @admin.display
    def visit_count(self, obj):
        return obj.visit_number

    @admin.display
    def gender(self, obj):
        return obj.patient.gender


class VisitInline(admin.TabularInline):
    form = VisitAdminForm
    model = Visit
    extra = 1
    show_change_link = True


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    inlines = [VisitInline]
    search_fields = ["patient_id"]
    search_help_text = "Patient ID"
    readonly_fields = ["created_at", "updated_at"]  # TODO: Might need specific user group.
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)

    list_display = ["patient_id", "gender", "age", "visit_count"]

    @admin.display
    def age(self, obj):
        age = 0
        for visit in obj.visit.all():
            age = max(age, visit.patient_age)
        return age

    @admin.display
    def visit_count(self, obj):
        return len(obj.visit.all())
