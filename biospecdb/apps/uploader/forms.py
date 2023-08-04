#from enum import auto
from pathlib import Path
import uuid

from django import forms
import django.core.files.uploadedfile
from django.core.validators import MinValueValidator, MaxValueValidator, MaxLengthValidator, FileExtensionValidator

from uploader.models import UploadedFile, Patient, SpectralData, Instrument, BioSample
import biospecdb.util
from .loaddata import save_data_to_db

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ["meta_data_file", "spectral_data_file"]

class DataInputForm(forms.Form):
        
    COVID_CHOICES = [
        ('negative', 'Negative'),
        ('positive', 'Positive')
    ]
        
    patient_id = forms.IntegerField(validators=[MinValueValidator(1)], label="Patient ID") 
    #Patient_id = forms.UUIDField(unique=True, primary_key=True, initial=uuid.uuid4, editable=False)
    
    Covid_RT_qPCR = forms.ChoiceField(choices=COVID_CHOICES, label="Covid RT qPCR results")
    Ct_gene_N = forms.FloatField(label="CTs (Gene N)")
    Ct_gene_ORF1ab = forms.FloatField(label="CTs (Gene ORF)")
    gender = forms.ChoiceField(required=False, choices=Patient.Gender.choices, label="Gender (M/F)")
    patient_age = forms.IntegerField(validators=[MinValueValidator(Patient.MIN_AGE), MaxValueValidator(Patient.MAX_AGE)], label="Age")
    days_symptomatic = forms.IntegerField(initial=None, validators=[MinValueValidator(0)])
    fever = forms.BooleanField(initial=False, required=False)
    dyspnoea = forms.BooleanField(initial=False, required=False)
    oxygen_saturation_lt_95 = forms.BooleanField(initial=False, required=False)
    cough = forms.BooleanField(initial=False, required=False)
    coryza = forms.BooleanField(initial=False, required=False)
    odinophagy = forms.BooleanField(initial=False, required=False)
    diarrhea = forms.BooleanField(initial=False, required=False)
    nausea = forms.BooleanField(initial=False, required=False)
    headache = forms.BooleanField(initial=False, required=False)
    weakness = forms.BooleanField(initial=False, required=False)
    anosmia = forms.BooleanField(initial=False, required=False)
    myalgia = forms.BooleanField(initial=False, required=False)
    lack_of_appetite = forms.BooleanField(initial=False, required=False)
    vomiting = forms.BooleanField(initial=False, required=False)
    suspicious_contact = forms.BooleanField(initial=False, required=False)
    chronic_pulmonary = forms.BooleanField(initial=False, required=False)
    cardiovascular_disease = forms.BooleanField(initial=False, required=False)
    diabetes = forms.BooleanField(initial=False, required=False)
    chronic_or_neuromuscular = forms.BooleanField(initial=False, required=False)
    spectra_measurement = forms.ChoiceField(initial=SpectralData.SpectralMeasurementKind.ATR_FTIR, validators=[MaxLengthValidator(128)],
                                            choices=SpectralData.SpectralMeasurementKind.choices, label="Spectra Measurement")
    spectrometer = forms.ChoiceField(initial=Instrument.Spectrometers.AGILENT_CORY_630, validators=[MaxLengthValidator(128)],
                                     choices=Instrument.Spectrometers.choices, label="Spectrometer")
    atr_crystal = forms.ChoiceField(initial=Instrument.SpectrometerCrystal.ZNSE, validators=[MaxLengthValidator(128)],
                                    choices=Instrument.SpectrometerCrystal.choices, label="ATR Crystal")
    acquisition_time = forms.IntegerField(required=False, label="Acquisition time [s]")
    n_coadditions = forms.IntegerField(initial=32, label="Number of coadditions")
    resolution = forms.IntegerField(required=False, label="Resolution [cm-1]")
    sample_type = forms.ChoiceField(initial=BioSample.SampleKind.PHARYNGEAL_SWAB,  validators=[MaxLengthValidator(128)],
                                    choices=BioSample.SampleKind.choices, label="Sample Type")
    sample_processing = forms.CharField(initial="None",required=False, validators=[MaxLengthValidator(128)], label="Sample Processing")
    freezing_temp = forms.FloatField(required=False, label="Freezing Temperature")
    thawing_time = forms.IntegerField(required=False, label="Thawing time")
 
    spectral_data = forms.FileField(label="Spectral data file", validators=[FileExtensionValidator(UploadedFile.FileFormats.choices())])
    #spectral_data.save(MEDIA_ROOT)
    
    #def __str__(self):
    #    return f"{self.Patient_id}"
    
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

        # Read in all data.
        meta_data = biospecdb.util.populate_meta_data(self.cleaned_data)
        spec_data = biospecdb.util.read_spectral_data_table(*_get_file_info(self.cleaned_data['spectral_data']))

        # This uses a join so returns the joined data so that it doesn't go to waste if needed, which it is here.
        joined_data = UploadedFile.join_with_validation(meta_data, spec_data)

        # Ingest into DB.
        save_data_to_db(None, None, joined_data=joined_data)
