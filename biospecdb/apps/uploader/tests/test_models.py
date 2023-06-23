from django.core.exceptions import ValidationError
import pytest

from uploader.models import Disease, Instrument, Patient, Symptom, Visit


class TestPatient:
    def test_creation(self):
        Patient(gender="MALE")
        Patient(gender="FEMALE")

    def test_db_creation(self, db):
        Patient.objects.create(gender="MALE")
        Patient.objects.create(gender="FEMALE")

        assert len(Patient.objects.all()) == 2

        Patient.objects.create(gender="MALE")
        assert len(Patient.objects.all()) == 3

        males = Patient.objects.filter(gender="MALE")
        females = Patient.objects.filter(gender="FEMALE")

        assert len(males) == 2
        assert len(females) == 1

        assert males[0].patient_id != males[1].patient_id

    def test_short_name(self):
        patient = Patient(gender="MALE")
        assert patient.short_id() in str(patient)

    def test_gender_validation(self, db):
        Patient(gender="MALE").full_clean()

        with pytest.raises(ValidationError):
            Patient(gender="blah").full_clean()

    def test_fixture_data(self, db, patients):
        assert len(Patient.objects.all()) == 3
        assert Patient.objects.get(pk="437de0d7-6618-4445-bab2-03822310b0ef")


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

    def test_previous_visit_patient_age_validation(self, db, visits):
        visit = Visit.objects.create(patient=Patient.objects.get(pk="437de0d7-6618-4445-bab2-03822310b0ef"),
                                     previous_visit=Visit.objects.get(pk=1),
                                     patient_age=20)
        with pytest.raises(ValidationError):
            visit.full_clean()


class TestDisease:
    def test_fixture_data(self, db, diseases):
        disease = Disease.objects.get(pk=1)
        assert disease.name == "Ct_gene_N"
        assert disease.value_class == Disease.Types.FLOAT


class TestInstrument:
    def test_fixture_data(self, db, instruments):
        instrument = Instrument.objects.get(pk=1)
        assert instrument.spectrometer == "AGILENT_COREY_630"
        assert instrument.atr_crystal == "ZNSE"


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
                                         disease=Disease.objects.get(name="fever"),
                                         days_symptomatic=7,
                                         disease_value=10)
        with pytest.raises(ValidationError):
            symptom.full_clean()


class TestBioSample:
    ...


class TestSpectralData:
    ...
