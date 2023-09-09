import django.core.files
import pytest

from uploader.models import UploadedFile, Patient, Visit, BioSample, SpectralData, Instrument, Disease
from uploader.forms import DataInputForm
from conftest import DATA_PATH


class TestDataInputForm:
    @pytest.mark.parametrize("file_ext", UploadedFile.FileFormats.list())
    def test_upload_without_error(self, db, file_ext):
        spectral_file_path = (DATA_PATH/"sample").with_suffix(file_ext)
        with spectral_file_path.open(mode="rb") as spectral_record:
            data_input_form = DataInputForm(
                data={
                    "patient_id": 1,
                    "gender": 'M',
                    "days_symptomatic": 1,
                    "patient_age": 1,
                    "spectra_measurement": 'ATR_FTIR',
                    "spectrometer": 'AGILENT_CORY_630',
                    "atr_crystal": 'ZNSE',
                    "acquisition_time": 1,
                    "n_coadditions": 32,
                    "resolution": 0,
                    "sample_type": 'PHARYNGEAL_SWAB',
                    "sample_processing": 'None',
                    "freezing_temp": 0,
                    "thawing_time": 0,
                },
                files={
                    "spectral_data": django.core.files.File(spectral_record, name=spectral_file_path.name)
                }
            )
            
            form_is_valid = data_input_form.is_valid()
            assert form_is_valid is True  # This asserts that the form is valid.

            form_has_changed = data_input_form.has_changed()
            assert form_has_changed is True  # This asserts that the form has changed.

    def test_mock_data_from_form_and_spectral_file_fixture(self, mock_data_from_form_and_spectral_file):
        n_patients = 1
        assert len(Patient.objects.all()) == n_patients
        assert len(Visit.objects.all()) == n_patients
        assert len(BioSample.objects.all()) == n_patients
        assert len(SpectralData.objects.all()) == n_patients
        
        gender_exists = Patient.objects.filter(gender='M').exists()
        assert gender_exists
        
        patient_age_exists = Visit.objects.filter(patient_age=1).exists()
        assert patient_age_exists

        spectra_measurement_exists = SpectralData.objects.filter(spectra_measurement='ATR_FTIR').exists()
        assert spectra_measurement_exists
        
        acquisition_time_exists = SpectralData.objects.filter(acquisition_time=1).exists()
        assert acquisition_time_exists
        
        n_coadditions_exists = SpectralData.objects.filter(n_coadditions=32).exists()
        assert n_coadditions_exists
        
        resolution_exists = SpectralData.objects.filter(resolution=0).exists()
        assert resolution_exists
        
        spectrometer_exists = Instrument.objects.filter(spectrometer='AGILENT_CORY_630').exists()
        assert spectrometer_exists
        
        atr_crystal_exists = Instrument.objects.filter(atr_crystal='ZNSE').exists()
        assert atr_crystal_exists
        
        sample_type_exists = BioSample.objects.filter(sample_type='PHARYNGEAL_SWAB').exists()
        assert sample_type_exists
        
        sample_processing_exists = BioSample.objects.filter(sample_processing='None').exists()
        assert sample_processing_exists
        
        freezing_temp_exists = BioSample.objects.filter(freezing_temp=0).exists()
        assert freezing_temp_exists
        
        thawing_time_exists = BioSample.objects.filter(thawing_time=0).exists()
        assert thawing_time_exists
        
        
    def test_dynamic_form_rendering(self, mock_data_from_form_and_spectral_file):
        spectral_file_path = (DATA_PATH/"sample").with_suffix(UploadedFile.FileFormats.XLSX)
        
        # Add new disease
        meningitis = Disease(
            name = 'Meningitis',
            description = 'An inflammation of the protective membranes covering the brain and spinal cord',
            alias = 'meningitis',
            value_class = 'BOOL',
        )
        meningitis.save()
        
        with spectral_file_path.open(mode="rb") as spectral_record:
            data_input_form = DataInputForm(
                data={
                    "patient_id": 1,
                    "gender": 'M',
                    "days_symptomatic": 1,
                    "patient_age": 1,
                    "spectra_measurement": 'ATR_FTIR',
                    "spectrometer": 'AGILENT_CORY_630',
                    "atr_crystal": 'ZNSE',
                    "acquisition_time": 1,
                    "n_coadditions": 32,
                    "resolution": 0,
                    "sample_type": 'PHARYNGEAL_SWAB',
                    "sample_processing": 'None',
                    "freezing_temp": 0,
                    "thawing_time": 0,
                },
                files={
                    "spectral_data": django.core.files.File(spectral_record, name=spectral_file_path.name)
                }
            )
            data_input_form.is_valid()
            
        meningitis_exists = Disease.objects.filter(name='Meningitis').exists()
        assert meningitis_exists # This asserts that the Meningitis disease exists in database.
        
        meningit_exists = Disease.objects.filter(name='Meningit').exists()
        assert not meningit_exists # This asserts that the Meningit disease exists in database.
