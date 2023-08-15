import pandas as pd
from django import forms

from uploader.models import UploadedFile, Patient, SpectralData, Instrument, BioSample, Symptom, Disease, Visit, \
                            POSITIVE, NEGATIVE
from biospecdb.util import read_spectral_data_table, get_file_info
from .loaddata import save_data_to_db

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["meta_data_file", "spectral_data_file"]

class DataInputForm(forms.Form):
        
    patient_id = forms.IntegerField(initial=False, required=True, label="Patient ID")
    gender = forms.ChoiceField(required=not Patient.gender.field.blank,
                               choices=Patient.Gender.choices,
                               label=Patient.gender.field.verbose_name)
    days_symptomatic = forms.IntegerField(initial=Symptom.days_symptomatic.field.default,
                                          label=Symptom.days_symptomatic.field.verbose_name)
    patient_age = forms.IntegerField(label=Visit.patient_age.field.verbose_name)
    spectra_measurement = forms.ChoiceField(choices=SpectralData.SpectralMeasurementKind.choices,
                                            label=SpectralData.spectra_measurement.field.verbose_name)
    spectrometer = forms.ChoiceField(choices=Instrument.Spectrometers.choices,
                                     label=Instrument.spectrometer.field.verbose_name)
    atr_crystal = forms.ChoiceField(choices=Instrument.SpectrometerCrystal.choices,
                                    label=Instrument.atr_crystal.field.verbose_name)
    acquisition_time = forms.IntegerField(required=not SpectralData.acquisition_time.field.blank,
                                          label=SpectralData.acquisition_time.field.verbose_name)
    n_coadditions = forms.IntegerField(initial=SpectralData.n_coadditions.field.default,
                                       label=SpectralData.n_coadditions.field.verbose_name)
    resolution = forms.IntegerField(required=not SpectralData.resolution.field.blank,
                                    label=SpectralData.resolution.field.verbose_name)
    sample_type = forms.ChoiceField(choices=BioSample.SampleKind.choices,
                                    label=BioSample.sample_type.field.verbose_name)
    sample_processing = forms.CharField(initial=BioSample.sample_processing.field.default,
                                        required=not BioSample.sample_processing.field.blank,
                                        label=BioSample.sample_processing.field.verbose_name)
    freezing_temp = forms.FloatField(required=not BioSample.freezing_temp.field.blank,
                                     label=BioSample.freezing_temp.field.verbose_name)
    thawing_time = forms.IntegerField(required=not BioSample.thawing_time.field.blank,
                                      label=BioSample.thawing_time.field.verbose_name)
    spectral_data = forms.FileField(label="Spectral data file")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for disease in Disease.objects.all(): # Dynamically add disease fields from the Disease table
            if (field_type := disease.value_class) == "BOOL":
                field_type = forms.BooleanField(initial=False, required=False, label=disease.alias)
            elif field_type == "FLOAT":
                field_type = forms.FloatField(initial=False, required=False, label=disease.alias)
            elif field_type == "STR":
                field_type = forms.ChoiceField(required=False, label=disease.alias,
                                               choices=[(NEGATIVE, 'Negative'), (POSITIVE, 'Positive')])
            self.fields[disease.name] = field_type

    def populate_meta_data(self):
        # Create a dictionary from the cleaned form data
        data = {}
        for key, value in self.cleaned_data.items():
            label = self.fields[key].label
            if label:
                data[label] = value
            else:
                data[key] = value
        data.pop("Spectral data file") # This is not a part of meta data, so should be removed.
        df = pd.DataFrame(data, index=[data['Patient ID']])
        canonic_data = df.rename(columns=lambda x: x.lower())
        return canonic_data

    def clean(self):
        """ Model validation. """

        super().clean()

        # Read in all data
        meta_data = self.populate_meta_data()
        spec_data = read_spectral_data_table(*get_file_info(self.cleaned_data['spectral_data']))
 
        # This uses a join so returns the joined data so that it doesn't go to waste if needed, which it is here.
        joined_data = UploadedFile.join_with_validation(meta_data, spec_data)

        # Ingest into DB.
        save_data_to_db(None, None, joined_data=joined_data)
