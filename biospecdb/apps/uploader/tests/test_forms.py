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
                    "patient_id": "4efb03c5-27cd-4b40-82d9-c602e0ef7b80",
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

        assert data_input_form.is_valid(), data_input_form.errors.as_data()

    def test_mock_data_from_form_and_spectral_file_fixture(self, mock_data_from_form_and_spectral_file):
        n_patients = 1
        assert len(Patient.objects.all()) == n_patients
        assert len(Visit.objects.all()) == n_patients
        assert len(BioSample.objects.all()) == n_patients
        assert len(SpectralData.objects.all()) == n_patients

        assert Patient.objects.filter(gender='M').exists()
        assert Visit.objects.filter(patient_age=1).exists()
        assert SpectralData.objects.filter(spectra_measurement='ATR_FTIR').exists()
        assert SpectralData.objects.filter(acquisition_time=1).exists()
        assert SpectralData.objects.filter(n_coadditions=32).exists()
        assert SpectralData.objects.filter(resolution=0).exists()
        assert Instrument.objects.filter(spectrometer='AGILENT_CORY_630').exists()
        assert Instrument.objects.filter(atr_crystal='ZNSE').exists()
        assert BioSample.objects.filter(sample_type='PHARYNGEAL_SWAB').exists()
        assert BioSample.objects.filter(sample_processing='None').exists()
        assert BioSample.objects.filter(freezing_temp=0).exists()
        assert BioSample.objects.filter(thawing_time=0).exists()

    def test_dynamic_form_rendering(self, mock_data_from_form_and_spectral_file):
        spectral_file_path = (DATA_PATH/"sample").with_suffix(UploadedFile.FileFormats.XLSX)
        
        # Add new disease
        meningitis = Disease(
            name='Meningitis',
            description='An inflammation of the protective membranes covering the brain and spinal cord',
            alias='meningitis',
            value_class='BOOL',
        )
        meningitis.save()
        
        with spectral_file_path.open(mode="rb") as spectral_record:
            data_input_form = DataInputForm(
                data={
                    "patient_id": "4efb03c5-27cd-4b40-82d9-c602e0ef7b80",
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
        assert data_input_form.is_valid(), data_input_form.errors.as_data()
            
        assert Disease.objects.filter(name='Meningitis').exists()
        assert not Disease.objects.filter(name='Meningit').exists()
