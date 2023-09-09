import pandas as pd
from django import forms

from uploader.models import UploadedFile, Patient, SpectralData, Instrument, BioSample, Symptom, Disease, Visit
from biospecdb.util import read_spectral_data_table, get_file_info
from .loaddata import save_data_to_db

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["meta_data_file", "spectral_data_file"]

class NaNValuesException(Exception):
    def __init__(self, message="NaN values found in the joined DataFrame"):
        self.message = message
        super().__init__(self.message)
        
class DataInputForm(forms.Form):
        
    patient_id = forms.IntegerField(required=True,
                                    initial=False,
                                    label="Patient ID")
    gender = forms.ChoiceField(required=not Patient.gender.field.blank,
                               initial=Patient.gender.field.default,
                               label=Patient.gender.field.verbose_name,
                               choices=Patient.Gender.choices)
    days_symptomatic = forms.IntegerField(required=not Symptom.days_symptomatic.field.blank,
                                          initial=Symptom.days_symptomatic.field.default,
                                          label=Symptom.days_symptomatic.field.verbose_name)
    patient_age = forms.IntegerField(required=not Visit.patient_age.field.blank,
                                     initial=Visit.patient_age.field.default,
                                     label=Visit.patient_age.field.verbose_name)
    spectra_measurement = forms.ChoiceField(required=not SpectralData.spectra_measurement.field.blank,
                                            initial=SpectralData.spectra_measurement.field.default,
                                            label=SpectralData.spectra_measurement.field.verbose_name,
                                            choices=SpectralData.SpectralMeasurementKind.choices)
    spectrometer = forms.ChoiceField(required=not Instrument.spectrometer.field.blank,
                                     initial=Instrument.spectrometer.field.default,
                                     label=Instrument.spectrometer.field.verbose_name,
                                     choices=Instrument.Spectrometers.choices)
    atr_crystal = forms.ChoiceField(required=not Instrument.atr_crystal.field.blank,
                                    initial=Instrument.atr_crystal.field.default,
                                    label=Instrument.atr_crystal.field.verbose_name,
                                    choices=Instrument.SpectrometerCrystal.choices)
    acquisition_time = forms.IntegerField(required=not SpectralData.acquisition_time.field.blank,
                                          initial=SpectralData.acquisition_time.field.default,
                                          label=SpectralData.acquisition_time.field.verbose_name)
    n_coadditions = forms.IntegerField(required=not SpectralData.n_coadditions.field.blank,
                                       initial=SpectralData.n_coadditions.field.default,
                                       label=SpectralData.n_coadditions.field.verbose_name)
    resolution = forms.IntegerField(required=not SpectralData.resolution.field.blank,
                                    initial=SpectralData.resolution.field.default,
                                    label=SpectralData.resolution.field.verbose_name)
    sample_type = forms.ChoiceField(required=not BioSample.sample_type.field.blank,
                                    initial=BioSample.sample_type.field.default,
                                    label=BioSample.sample_type.field.verbose_name,
                                    choices=BioSample.SampleKind.choices)
    sample_processing = forms.CharField(required=not BioSample.sample_processing.field.blank,
                                        initial=BioSample.sample_processing.field.default,
                                        label=BioSample.sample_processing.field.verbose_name)
    freezing_temp = forms.FloatField(required=not BioSample.freezing_temp.field.blank,
                                     initial=BioSample.freezing_temp.field.default,
                                     label=BioSample.freezing_temp.field.verbose_name)
    thawing_time = forms.IntegerField(required=not BioSample.thawing_time.field.blank,
                                      initial=BioSample.thawing_time.field.default,
                                      label=BioSample.thawing_time.field.verbose_name)
    spectral_data = forms.FileField(label="Spectral data file")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for disease in Disease.objects.all(): # Dynamically add disease fields from the Disease table
            if (field_type := disease.value_class) == "FLOAT":
                field_type = forms.FloatField(required=False,
                                              initial=False,
                                              label=disease.alias)
            elif field_type == "STR":
                field_type = forms.CharField(required=False,
                                             initial='',
                                             label=disease.alias)
            elif field_type == "BOOL":
                field_type = forms.BooleanField(required=False,
                                                initial=False,
                                                label=disease.alias)
                #To be reconsidered later
                #field_type = forms.BooleanField(required=False,
                #                                label=disease.alias,
                #                                widget=forms.NullBooleanSelect)
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
        
        if joined_data[spec_data.columns].isna().any().any():
            # No match between meta_data and spec_data based on patient_id field
            raise NaNValuesException
        else:
            # Ingest into DB.
            save_data_to_db(None, None, joined_data=joined_data)
