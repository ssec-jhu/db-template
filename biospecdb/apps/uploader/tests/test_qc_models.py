import pytest
from django.core.exceptions import ValidationError

from uploader.models import QCAnnotation, QCAnnotator, SpectralData


def test_qcannotators_django_fixture(qcannotators):
    annotators = QCAnnotator.objects.all()
    assert len(annotators) == 1
    assert annotators[0].name == "sum"


def test_qualified_class_name_import_validation_validator(db):
    with pytest.raises(ValidationError, match="cannot be imported"):
        QCAnnotator(name="fail", qualified_class_name=1).full_clean()


def test_unique_annotator(qcannotators):
    with pytest.raises(ValidationError, match="already exists"):
        QCAnnotator(name="sum", qualified_class_name="biospecdb.qc.qcfilter.QcSum").full_clean()

    with pytest.raises(ValidationError, match="already exists"):
        QCAnnotator(name="huh", qualified_class_name="biospecdb.qc.qcfilter.QcSum").full_clean()

    with pytest.raises(ValidationError, match="already exists"):
        QCAnnotator(name="sum", qualified_class_name="biospecdb.qc.qcfilter.QcFilter").full_clean()


def test_new_annotation(qcannotators, mock_data_from_files):
    annotator = QCAnnotator.objects.get(name="sum")
    spectral_data = SpectralData.objects.all()[0]
    annotation = QCAnnotation(annotator=annotator, spectral_data=spectral_data)
    annotation.full_clean()
    assert pytest.approx(float(annotation.value)) == 915.3270367661034
