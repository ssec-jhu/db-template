from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
import django.core.files
from django.db.utils import IntegrityError
import pytest

from uploader.io import read_meta_data
from uploader.models import BioSample, Disease, Instrument, Patient, SpectralData, Symptom, Visit, UploadedFile,\
    get_center, Center
from uploader.loaddata import save_data_to_db, TEMP_FILENAME_PREFIX
from user.models import Center as UserCenter
from uploader.models import Center as UploaderCenter
import biospecdb.util
from uploader.tests.conftest import DATA_PATH


@pytest.mark.django_db(databases=["default", "bsr"])
class TestPatient:
    def test_creation(self, center):
        Patient(gender=Patient.Gender.MALE, center=center).full_clean()
        Patient(gender=Patient.Gender.FEMALE, center=center).full_clean()
        Patient(gender=Patient.Gender.UNSPECIFIED, center=center).full_clean()

    def test_db_creation(self, center):
        Patient.objects.create(gender=Patient.Gender.MALE, center=center).full_clean()
        Patient.objects.create(gender=Patient.Gender.FEMALE, center=center).full_clean()
        Patient.objects.create(gender=Patient.Gender.UNSPECIFIED, center=center).full_clean()

        assert len(Patient.objects.all()) == 3

        Patient.objects.create(gender=Patient.Gender.MALE, center=center).full_clean()
        assert len(Patient.objects.all()) == 4

        males = Patient.objects.filter(gender=Patient.Gender.MALE, center=center)
        females = Patient.objects.filter(gender=Patient.Gender.FEMALE, center=center)
        unspecified = Patient.objects.filter(gender=Patient.Gender.UNSPECIFIED, center=center)
        
        assert len(males) == 2
        assert len(females) == 1
        assert len(unspecified) == 1
        
        assert males[0].patient_id != males[1].patient_id

    def test_short_name(self, center):
        patient = Patient(gender=Patient.Gender.MALE, center=center)
        patient.full_clean()
        assert patient.short_id() in str(patient)

    def test_gender_validation(self, center):
        Patient(gender=Patient.Gender.MALE, center=center).full_clean()

        with pytest.raises(ValidationError):
            Patient(gender="blah").full_clean()

    def test_fixture_data(self, db, patients):
        assert len(Patient.objects.all()) == 3
        assert Patient.objects.get(pk="437de0d7-6618-4445-bab2-03822310b0ef")

    def test_editable_patient_id(self, center):
        patient_id = uuid4()
        Patient.objects.create(patient_id=patient_id, gender=Patient.Gender.FEMALE, center=center)
        assert Patient.objects.get(pk=patient_id)

    def test_center_validation(self, centers):
        center = UploaderCenter.objects.get(name="SSEC")
        assert UserCenter.objects.filter(pk=center.pk).exists()
        assert UploaderCenter.objects.filter(pk=center.pk).exists()

        # OK.
        patient_id = uuid4()
        patient = Patient(patient_id=patient_id, gender=Patient.Gender.FEMALE, center=center)
        patient.full_clean()

        # Not OK.
        patient_id = uuid4()
        with pytest.raises(ValueError, match="Cannot assign"):
            patient = Patient(patient_id=patient_id,
                              gender=Patient.Gender.FEMALE,
                              center=UserCenter.objects.get(name="SSEC"))

    def test_unique_cid_center_id(self, centers):
        center = UploaderCenter.objects.get(name="SSEC")
        cid = uuid4()
        Patient.objects.create(patient_id=uuid4(),
                               gender=Patient.Gender.FEMALE,
                               center=center,
                               patient_cid=cid)
        # OK.
        Patient.objects.create(patient_id=uuid4(),
                               gender=Patient.Gender.FEMALE,
                               center=center,
                               patient_cid=uuid4())

        # OK.
        Patient.objects.create(patient_id=uuid4(),
                               gender=Patient.Gender.FEMALE,
                               center=UploaderCenter.objects.get(name="Imperial College London"),
                               patient_cid=cid)

        # Not OK.
        with pytest.raises(IntegrityError, match="UNIQUE constraint failed:"):
            Patient.objects.create(patient_id=uuid4(),
                                   gender=Patient.Gender.FEMALE,
                                   center=center,
                                   patient_cid=cid)

    def test_pi_cid_validation(self, centers):
        id = uuid4()
        patient = Patient(patient_id=id,
                          gender=Patient.Gender.UNSPECIFIED,
                          patient_cid=id,
                          center=Center.objects.get(name="SSEC"))
        with pytest.raises(ValidationError, match="Patient ID and patient CID cannot be the same"):
            patient.full_clean()


@pytest.mark.django_db(databases=["default", "bsr"])
class TestVisit:
    def test_visit_number(self, db, visits):
        assert Visit.objects.get(pk=1).visit_number == 1
        assert Visit.objects.get(pk=3).visit_number == 2

    def test_walk(self, db, visits):
        v1 = Visit.objects.get(pk=1)
        v2 = Visit.objects.get(pk=3)
        assert v1.patient.pk == v2.patient.pk

    def test_previous_visit_same_patient_validation(self, db, visits):
        visit = Visit.objects.get(pk=2)
        visit.previous_visit = Visit.objects.get(pk=1)
        with pytest.raises(ValidationError):
            visit.full_clean()
    
    def test_auto_find_previous_visit(self, db, visits):
        visit = Visit.objects.get(pk=4)
        visit.full_clean()
        previous_visit = Visit.objects.get(pk=2)
        assert visit.previous_visit == previous_visit

    def test_previous_visit_patient_age_validation(self, db, visits):
        previous_visit = Visit.objects.get(pk=1)
        visit = Visit(patient=previous_visit.patient,
                      previous_visit=previous_visit,
                      patient_age=previous_visit.patient_age - 1)
        with pytest.raises(ValidationError, match="Previous visit must NOT be older than this one"):
            visit.full_clean()

    def test_circular_previous_visit(self, db, visits):
        visit = Visit.objects.get(pk=1)
        visit.previous_visit = visit
        with pytest.raises(ValidationError, match="Previous visit cannot not be this current visit"):
            visit.full_clean()


@pytest.mark.django_db(databases=["default", "bsr"])
class TestDisease:
    def test_fixture_data(self, db, diseases):
        disease = Disease.objects.get(pk=1)
        assert disease.name == "Ct_gene_N"
        assert disease.value_class == Disease.Types.FLOAT

    def test_name_uniqueness(self, db):
        Disease.objects.create(name="A", description="blah", alias="a")
        with pytest.raises(IntegrityError, match="unique_disease_name"):
            Disease.objects.create(name="a", description="blah", alias="b")

    def test_alias_uniqueness(self, db):
        Disease.objects.create(name="A", description="blah", alias="a")
        with pytest.raises(IntegrityError, match="unique_alias_name"):
            Disease.objects.create(name="b", description="blah", alias="A")


@pytest.mark.django_db(databases=["default", "bsr"])
class TestInstrument:
    def test_fixture_data(self, db, instruments):
        instrument = Instrument.objects.get(pk=1)
        assert instrument.spectrometer == "Agilent Cory 630"
        assert instrument.atr_crystal == "ZnSe"

    def test_new(self, db, instruments):
        Instrument.objects.create(spectrometer="new instrument", atr_crystal="new crystal")
        assert len(Instrument.objects.all()) == 2
        assert Instrument.objects.filter(spectrometer="new instrument").exists()
        assert Instrument.objects.filter(atr_crystal="new crystal").exists()

    def test_uniqueness(self, db, instruments):
        # OK
        Instrument.objects.create(spectrometer="Agilent Cory 630", atr_crystal="new crystal")

        # Not OK
        with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
            Instrument.objects.create(spectrometer="Agilent Cory 630", atr_crystal="ZnSe")


@pytest.mark.django_db(databases=["default", "bsr"])
class TestSymptom:
    def test_days_symptomatic_validation(self, db, diseases, visits):
        visit = Visit.objects.get(pk=1)
        age = visit.patient_age
        symptom = Symptom.objects.create(visit=visit,
                                         disease=Disease.objects.get(name="fever"),
                                         days_symptomatic=age * 365 + 1)
        with pytest.raises(ValidationError):
            symptom.full_clean()

    def test_disease_value_validation(self, db, diseases, visits):
        symptom = Symptom.objects.create(visit=Visit.objects.get(pk=1),
                                         disease=Disease.objects.get(name="Ct_gene_N"),
                                         days_symptomatic=7,
                                         disease_value="strings can't cast to floats")
        with pytest.raises(ValidationError):
            symptom.full_clean()

    @pytest.mark.parametrize("value", (True, False))
    def test_disease_value_bool_cast(self, db, diseases, visits, value):
        symptom = Symptom.objects.create(visit=Visit.objects.get(pk=1),
                                         disease=Disease.objects.get(name="fever"),
                                         days_symptomatic=7,
                                         disease_value=str(value))
        symptom.full_clean()
        assert symptom.disease_value is value

    def test_center_validation(self, centers):
        center = Center.objects.get(name="SSEC")
        patient = Patient.objects.create(center=center)
        visit = Visit.objects.create(patient_age=40, patient=patient)

        # OK.
        disease = Disease.objects.create(name="snuffles", alias="snuffles", center=center)
        Symptom(visit=visit, disease=disease).full_clean()

        # OK.
        disease = Disease.objects.create(name="extra_snuffles", alias="extra snuffles", center=None)
        Symptom(visit=visit, disease=disease).full_clean()

        # Not OK.
        center
        disease = Disease.objects.create(name="even_more_snuffles",
                                         alias="even more snuffles",
                                         center=Center.objects.get(name="Imperial College London"))
        with pytest.raises(ValidationError, match="Patient symptom disease category must belong to patient center:"):
            Symptom(visit=visit, disease=disease).full_clean()


@pytest.mark.django_db(databases=["default", "bsr"])
class TestBioSample:
    ...


@pytest.mark.django_db(databases=["default", "bsr"])
class TestSpectralData:
    def test_files_added(self, mock_data_from_files):
        n_patients = 10
        assert len(SpectralData.objects.all()) == n_patients
        for obj in SpectralData.objects.all():
            assert Path(obj.data.name).exists()

    def test_temp_files_deleted(self, mock_data_from_files):
        n_patients = 10
        assert len(SpectralData.objects.all()) == n_patients
        filename = Path(SpectralData.objects.all()[0].data.name)
        assert filename.parent.exists()
        assert filename.parent.is_dir()
        assert len(list(filename.parent.glob('*'))) == n_patients
        assert not list(filename.parent.glob(f"*{TEMP_FILENAME_PREFIX}*"))

    @pytest.mark.skip("Unimplemented See #141")
    def test_all_files_deleted_upon_transaction_failure(self):
        # I'm not sure how to mock this... See https://github.com/ssec-jhu/biospecdb/issues/141
        ...


@pytest.mark.django_db(databases=["default", "bsr"])
class TestUploadedFile:
    @pytest.mark.parametrize("file_ext", UploadedFile.FileFormats.list())
    def test_upload_without_error(self, db, diseases, instruments, file_ext, center):
        meta_data_path = (DATA_PATH/"meta_data").with_suffix(file_ext)
        spectral_file_path = (DATA_PATH / "spectral_data").with_suffix(file_ext)
        with meta_data_path.open(mode="rb") as meta_data, spectral_file_path.open(mode="rb") as spectral_data:
            data_upload = UploadedFile(meta_data_file=django.core.files.File(meta_data,
                                                                             name=meta_data_path.name),
                                       spectral_data_file=django.core.files.File(spectral_data,
                                                                                 name=spectral_file_path.name),
                                       center=center)
            data_upload.clean()
            data_upload.save()

    def test_mock_data_from_files_fixture(self, mock_data_from_files):
        n_patients = 10
        assert len(UploadedFile.objects.all()) == 1
        assert len(Patient.objects.all()) == n_patients
        assert len(Visit.objects.all()) == n_patients
        assert len(BioSample.objects.all()) == n_patients
        assert len(SpectralData.objects.all()) == n_patients

    def test_center(self, mock_data_from_files):
        n_patients = len(Patient.objects.all())
        assert n_patients == 10
        center = Center.objects.get(name="SSEC")
        assert n_patients == len(Patient.objects.filter(center=center))
        assert not Patient.objects.filter(center=None)

    def test_mock_data_fixture(self, mock_data):
        n_patients = 10
        assert len(Patient.objects.all()) == n_patients
        assert len(Visit.objects.all()) == n_patients
        assert len(BioSample.objects.all()) == n_patients
        assert len(SpectralData.objects.all()) == n_patients

    def test_number_symptoms(self, db, diseases, instruments, center):
        """ The total number of symptoms := N_patients * N_diseases. """
        assert len(Patient.objects.all()) == 0  # Assert empty.

        save_data_to_db(DATA_PATH / "meta_data.csv",
                        DATA_PATH / "spectral_data.csv",
                        center=center)

        n_patients = len(Patient.objects.all())
        n_diseases = len(Disease.objects.all())
        n_symptoms = len(Symptom.objects.all())

        # Assert not empty.
        assert n_patients > 0
        assert n_diseases > 0
        assert n_symptoms > 0

        # When Covid_RT_qPCR is negative both Ct_gene_N & Ct_gene_ORF1ab symptoms will be null and omitted. This must be
        # accounted for in the total.
        n_empty_covid_symptoms = len((Symptom.objects.filter(disease=Disease.objects.get(name="Covid_RT_qPCR")))
                                     .filter(disease_value="Negative"))
        assert n_symptoms == n_patients * n_diseases - n_empty_covid_symptoms * 2

    def test_days_of_symptoms(self, mock_data_from_files):
        week_long_symptoms = Symptom.objects.filter(days_symptomatic=7)
        assert len(week_long_symptoms) > 1
        assert week_long_symptoms[0].days_symptomatic == 7
        null_days = len(Symptom.objects.filter(days_symptomatic=None))
        assert null_days > 1
        assert null_days < len(Symptom.objects.all())

    @pytest.mark.parametrize("file_ext", UploadedFile.FileFormats.list())
    def test_patient_ids(self, mock_data_from_files, file_ext):
        meta_data_path = (DATA_PATH / "meta_data").with_suffix(file_ext)
        df = read_meta_data(meta_data_path)

        all_patients = Patient.objects.all()

        assert len(all_patients) == len(df)
        for index in df.index:
            assert all_patients.get(pk=index)

    @pytest.mark.parametrize("file_ext", UploadedFile.FileFormats.list())
    def test_index_match_validation(self, db, diseases, instruments, file_ext, tmp_path):
        meta_data_path = (DATA_PATH / "meta_data").with_suffix(file_ext)

        biospecdb.util.mock_bulk_spectral_data(path=tmp_path)
        spectral_file_path = tmp_path / "spectral_data.csv"
        with meta_data_path.open(mode="rb") as meta_data, spectral_file_path.open(mode="rb") as spectral_data:
            data_upload = UploadedFile(meta_data_file=django.core.files.File(meta_data,
                                                                             name=meta_data_path.name),
                                       spectral_data_file=django.core.files.File(spectral_data,
                                                                                 name=spectral_file_path.name))
            with pytest.raises(ValidationError, match="Patient ID mismatch."):
                data_upload.clean()


@pytest.mark.django_db(databases=["default", "bsr"])
def test_get_center(centers, mock_data_from_files):
    center = Center.objects.get(name="SSEC")
    assert get_center(center) is center

    from user.models import Center as UserCenter
    assert get_center(UserCenter.objects.get(pk=center.pk)) == center

    patient = Patient.objects.all()[0]
    patient.center = center
    patient.full_clean()
    patient.save()

    assert get_center(patient) is center

    for visit in patient.visit.all():
        assert get_center(visit) is center

    for bio_sample in visit.bio_sample.all():
        assert get_center(bio_sample) is center

    for spectral_data in bio_sample.spectral_data.all():
        assert get_center(spectral_data) is center

    for symptom in Symptom.objects.filter(visit__patient__center=center):
        assert get_center(symptom) == center
        # assert get_center(symptom.disease) is center  # TODO: Not yet related in disease.json fixture.
