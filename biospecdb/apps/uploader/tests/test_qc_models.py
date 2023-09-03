import pytest
from django.conf import settings
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
    assert annotation.value is None
    annotation.full_clean()
    assert pytest.approx(float(annotation.value)) == 915.3270367661034


expected_sum_results = [915.3270367661034,
                        905.2060788485444,
                        897.5824088776908,
                        876.2542534234417,
                        902.9216637136165,
                        915.8926854978613,
                        895.7923513684976,
                        885.9432421888927,
                        913.9661052327297,
                        902.0836794874253]


@pytest.mark.parametrize("mock_data_from_files", [False], indirect=True)
def test_auto_annotate_settings(qcannotators, mock_data_from_files):
    annotations = QCAnnotation.objects.all()
    for annotation in annotations:
        assert annotation.value is None


@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)
def test_auto_annotate_with_new_spectral_data(qcannotators, mock_data_from_files):
    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results


def test_auto_annotate_with_new_default_annotator(monkeypatch, mock_data_from_files):
    for annotation in QCAnnotation.objects.all():
        assert annotation.value is None

    monkeypatch.setattr(settings, "RUN_DEFAULT_ANNOTATORS_WHEN_SAVED", True)

    annotator = QCAnnotator(name="sum", qualified_class_name="biospecdb.qc.qcfilter.QcSum")
    annotator.full_clean()
    annotator.save()

    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results
