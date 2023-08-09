from pathlib import Path
import pandas as pd
from django import forms
import django.core.files.uploadedfile
from django.core.validators import MaxLengthValidator

from uploader.models import UploadedFile, Patient, SpectralData, Instrument, BioSample, Symptom, Disease, Visit
import biospecdb.util
from .loaddata import save_data_to_db

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["meta_data_file", "spectral_data_file"]

class DataInputForm(forms.Form):
        
    patient_id = forms.IntegerField(initial=False, required=True, label="Patient ID")
    gender = forms.ChoiceField(required=False, choices=Patient.Gender.choices,
                               validators=Patient.gender.field.validators, label=Patient.gender.field.verbose_name)
    days_symptomatic = forms.IntegerField(initial=0, validators=Symptom.days_symptomatic.field.validators,
                                          label=Symptom.days_symptomatic.field.verbose_name)
    patient_age = forms.IntegerField(validators=Visit.patient_age.field.validators,
                                     label=Visit.patient_age.field.verbose_name)

    #Ct_gene_N = forms.FloatField(label="CTs (Gene N)")
    #Ct_gene_ORF1ab = forms.FloatField(label="CTs (Gene ORF)")
    #Covid_RT_qPCR = forms.ChoiceField(choices=COVID_CHOICES, label="Covid RT qPCR results")
    #suspicious_contact = forms.BooleanField(initial=False, required=False)
    #fever = forms.BooleanField(initial=False, required=False)
    #dyspnoea = forms.BooleanField(initial=False, required=False)
    #oxygen_saturation_lt_95 = forms.BooleanField(initial=False, required=False)
    #cough = forms.BooleanField(initial=False, required=False)
    #coryza = forms.BooleanField(initial=False, required=False)
    #odinophagy = forms.BooleanField(initial=False, required=False)
    #diarrhea = forms.BooleanField(initial=False, required=False)
    #nausea = forms.BooleanField(initial=False, required=False)
    #headache = forms.BooleanField(initial=False, required=False)
    #weakness = forms.BooleanField(initial=False, required=False)
    #anosmia = forms.BooleanField(initial=False, required=False)
    #myalgia = forms.BooleanField(initial=False, required=False)
    #lack_of_appetite = forms.BooleanField(initial=False, required=False)
    #vomiting = forms.BooleanField(initial=False, required=False)
    #chronic_pulmonary = forms.BooleanField(initial=False, required=False)
    #cardiovascular_disease = forms.BooleanField(initial=False, required=False)
    #diabetes = forms.BooleanField(initial=False, required=False)
    #chronic_or_neuromuscular = forms.BooleanField(initial=False, required=False)
    
    spectra_measurement = forms.ChoiceField(initial=SpectralData.SpectralMeasurementKind.ATR_FTIR,
                                            validators=[MaxLengthValidator(128)],
                                            choices=SpectralData.SpectralMeasurementKind.choices,
                                            label=SpectralData.spectra_measurement.field.verbose_name)
    spectrometer = forms.ChoiceField(initial=Instrument.Spectrometers.AGILENT_CORY_630,
                                     validators=[MaxLengthValidator(128)],choices=Instrument.Spectrometers.choices,
                                     label=Instrument.spectrometer.field.verbose_name)
    atr_crystal = forms.ChoiceField(initial=Instrument.SpectrometerCrystal.ZNSE, validators=[MaxLengthValidator(128)],
                                    choices=Instrument.SpectrometerCrystal.choices,
                                    label=Instrument.atr_crystal.field.verbose_name)
    acquisition_time = forms.IntegerField(required=False, label=SpectralData.acquisition_time.field.verbose_name)
    n_coadditions = forms.IntegerField(initial=32, label=SpectralData.n_coadditions.field.verbose_name)
    resolution = forms.IntegerField(required=False, label=SpectralData.resolution.field.verbose_name)
    sample_type = forms.ChoiceField(initial=BioSample.SampleKind.PHARYNGEAL_SWAB, validators=[MaxLengthValidator(128)],
                                    choices=BioSample.SampleKind.choices,
                                    label=BioSample.sample_type.field.verbose_name)
    sample_processing = forms.CharField(initial=BioSample.sample_processing.field.default, required=False,
                                        validators=[MaxLengthValidator(128)],
                                        label=BioSample.sample_processing.field.verbose_name)
    freezing_temp = forms.FloatField(required=False, label=BioSample.freezing_temp.field.verbose_name)
    thawing_time = forms.IntegerField(required=False, label=BioSample.thawing_time.field.verbose_name)
 
    spectral_data = forms.FileField(validators=UploadedFile.spectral_data_file.field.validators,
                                    label="Spectral data file")
    
    
    def __init__(self, *args, **kwargs):
        CHOICES = [
            ('negative', 'Negative'),
            ('positive', 'Positive')
        ]
        super().__init__(*args, **kwargs)
        for disease in Disease.objects.all():
            if (field_type := disease.value_class) == "BOOL":
                field_type = forms.BooleanField(initial=False, required=False, label=disease.alias)
            elif field_type == "FLOAT":
                field_type = forms.FloatField(initial=False, required=False, label=disease.alias)
            elif field_type == "STR":
                field_type = forms.ChoiceField(initial=False, required=False, choices=CHOICES, label=disease.alias)
            self.fields[disease.name] = field_type
    
    def __str__(self):
        return f"{self.patient_id}"

    def populate_meta_data(self):
        # Create a dictionary from the cleaned form data
        data = {}
        for key, value in self.cleaned_data.items():
            label = self.fields[key].label
            if label:
                data[label] = value
            else:
                data[key] = value
        data.pop("Spectral data file")
        df = pd.DataFrame(data, index=[data['Patient ID']])
        canonic_data = df.rename(columns=lambda x: x.lower())
        return canonic_data


    def clean(self):
        """ Model validation. """

        super().clean()

        def _get_file_info(file_wrapper):
            """ The actual file buffer is nested at different levels depending on container class. """
            if isinstance(file_wrapper, django.core.files.uploadedfile.TemporaryUploadedFile):
                file = file_wrapper.file.file
            elif isinstance(file_wrapper, django.core.files.File):
                file = file_wrapper.file
            else:
                raise NotImplementedError(type(file_wrapper))
            return file, Path(file_wrapper.name).suffix

        # Read in all data
        meta_data = self.populate_meta_data()
        spec_data = biospecdb.util.read_spectral_data_table(*_get_file_info(self.cleaned_data['spectral_data']))
 
        # This uses a join so returns the joined data so that it doesn't go to waste if needed, which it is here.
        joined_data = UploadedFile.join_with_validation(meta_data, spec_data)

        # Ingest into DB.
        save_data_to_db(None, None, joined_data=joined_data)
        