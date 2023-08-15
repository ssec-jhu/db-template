from django.core.exceptions import ValidationError
from django import forms
import django.core.files
from django.db.utils import IntegrityError
import pytest

from uploader.models import BioSample, Disease, Instrument, Patient, SpectralData, Symptom, Visit, UploadedFile
from uploader.forms import DataInputForm
from uploader.loaddata import save_data_to_db
from conftest import DATA_PATH


class TestDataInputForm:
    @pytest.mark.parametrize("file_ext", UploadedFile.FileFormats.list())
    def test_upload_without_error(self, db, diseases, instruments, file_ext):
        spectral_file_path = (DATA_PATH / "sample").with_suffix(file_ext)
        with spectral_file_path.open(mode="rb") as spectral_data_file:
            data_input_form = DataInputForm(patient_id=forms.IntegerField(initial=1,label="Patient ID"),
                                            spectral_data_file=django.core.files.File(label=spectral_file_path.name))
            data_input_form.clean()
            data_input_form.save()

    #def test_mock_data_from_files_fixture(self, mock_data_from_files):
    #    n_patients = 10
    #    assert len(UploadedFile.objects.all()) == 1
    #    assert len(Patient.objects.all()) == n_patients
    #    assert len(Visit.objects.all()) == n_patients
    #    assert len(BioSample.objects.all()) == n_patients
    #    assert len(SpectralData.objects.all()) == n_patients
#
    #def test_mock_data_fixture(self, mock_data):
    #    n_patients = 10
    #    assert len(Patient.objects.all()) == n_patients
    #    assert len(Visit.objects.all()) == n_patients
    #    assert len(BioSample.objects.all()) == n_patients
    #    assert len(SpectralData.objects.all()) == n_patients
#
    #def test_number_symptoms(self, db, diseases, instruments):
    #    """ The total number of symptoms := N_patients * N_diseases. """
    #    assert len(Patient.objects.all()) == 0  # Assert empty.
#
    #    save_data_to_db(DATA_PATH / "meta_data.csv",
    #                    DATA_PATH / "spectral_data.csv")
#
    #    n_patients = len(Patient.objects.all())
    #    n_diseases = len(Disease.objects.all())
    #    n_symptoms = len(Symptom.objects.all())
#
    #    # Assert not empty.
    #    assert n_patients > 0
    #    assert n_diseases > 0
    #    assert n_symptoms > 0
#
    #    # When Covid_RT_qPCR is negative both Ct_gene_N & Ct_gene_ORF1ab symptoms will be null and omitted. This must be
    #    # accounted for in the total.
    #    n_empty_covid_symptoms = len((Symptom.objects.filter(disease=Disease.objects.get(name="Covid_RT_qPCR")))
    #                                 .filter(disease_value="Negative"))
    #    assert n_symptoms == n_patients * n_diseases - n_empty_covid_symptoms * 2
#
    #def test_days_of_symptoms(self, mock_data_from_files):
    #    week_long_symptoms = Symptom.objects.filter(days_symptomatic=7)
    #    assert len(week_long_symptoms) > 1
    #    assert week_long_symptoms[0].days_symptomatic == 7
    #    null_days = len(Symptom.objects.filter(days_symptomatic=None))
    #    assert null_days > 1
    #    assert null_days < len(Symptom.objects.all())
