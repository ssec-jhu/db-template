import django.core.files
import pytest
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biospecdb.settings')
django.setup()

from uploader.models import UploadedFile, Patient, Visit, BioSample, SpectralData
from uploader.forms import DataInputForm
from conftest import DATA_PATH


class TestDataInputForm:
    @pytest.mark.parametrize("file_ext", UploadedFile.FileFormats.list())
    def test_upload_without_error(self, db, diseases, instruments, file_ext):
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
            data_input_form.is_valid()
            data_input_form.has_changed()


    def test_mock_data_from_form_and_spectral_file_fixture(self, mock_data_from_form_and_spectral_file):
        n_patients = 1
        assert len(Patient.objects.all()) == n_patients
        assert len(Visit.objects.all()) == n_patients
        assert len(BioSample.objects.all()) == n_patients
        assert len(SpectralData.objects.all()) == n_patients
