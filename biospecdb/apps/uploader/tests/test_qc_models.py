from io import StringIO

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils.module_loading import import_string

from uploader.models import QCAnnotation, QCAnnotator, SpectralData
import biospecdb.qc.qcfilter

import biospecdb.util


def test_qcannotators_django_fixture(qcannotators):
    annotators = QCAnnotator.objects.all()
    assert len(annotators) == 1
    assert annotators[0].name == "sum"


def test_qualified_class_name_import_validation_validator(db):
    with pytest.raises(ValidationError, match="cannot be imported"):
        QCAnnotator(name="fail", fully_qualified_class_name=1).full_clean()


def test_unique_annotator(qcannotators):
    with pytest.raises(ValidationError, match="already exists"):
        QCAnnotator(name="sum", fully_qualified_class_name="biospecdb.qc.qcfilter.QcSum").full_clean()

    with pytest.raises(ValidationError, match="already exists"):
        QCAnnotator(name="huh", fully_qualified_class_name="biospecdb.qc.qcfilter.QcSum").full_clean()

    with pytest.raises(ValidationError, match="already exists"):
        QCAnnotator(name="sum", fully_qualified_class_name="biospecdb.qc.qcfilter.QcFilter").full_clean()


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


@pytest.mark.parametrize("mock_data_from_files", [False], indirect=True)  # AUTO_ANNOTATE = False
def test_auto_annotate_settings(qcannotators, mock_data_from_files):
    annotations = QCAnnotation.objects.all()
    for annotation in annotations:
        assert annotation.value is None


# This test is just to demonstrate to anyone looking that the switch in mock_data_from_files isn't necessarily needed.
@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)  # AUTO_ANNOTATE = True
def test_pytest_fixture_order(mock_data_from_files, qcannotators):
    annotations = QCAnnotation.objects.all()
    for annotation in annotations:
        assert annotation.value is None


@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)  # AUTO_ANNOTATE = True
def test_auto_annotate_with_new_spectral_data(qcannotators, mock_data_from_files):
    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results


def test_auto_annotate_with_new_default_annotator(monkeypatch, mock_data_from_files):
    for annotation in QCAnnotation.objects.all():
        assert annotation.value is None

    monkeypatch.setattr(settings, "RUN_DEFAULT_ANNOTATORS_WHEN_SAVED", True)

    annotator = QCAnnotator(name="sum", fully_qualified_class_name="biospecdb.qc.qcfilter.QcSum")
    annotator.full_clean()
    annotator.save()

    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results


def test_empty_get_annotators(mock_data_from_files):
    for data in SpectralData.objects.all():
        assert len(data.get_annotators()) == 0


@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)  # AUTO_ANNOTATE = True
def test_get_annotators(qcannotators, mock_data_from_files):
    for data in SpectralData.objects.all():
        assert len(data.get_annotators()) == 1


@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)  # AUTO_ANNOTATE = True
def test_get_zero_unrun_annotators(qcannotators, mock_data_from_files):
    for data in SpectralData.objects.all():
        assert len(data.get_unrun_annotators()) == 0


@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)  # AUTO_ANNOTATE = True
def test_get_unrun_annotators(monkeypatch, qcannotators, mock_data_from_files):
    for data in SpectralData.objects.all():
        assert len(data.get_unrun_annotators()) == 0

    monkeypatch.setattr(settings, "RUN_DEFAULT_ANNOTATORS_WHEN_SAVED", False)

    annotator = QCAnnotator(name="tets", fully_qualified_class_name="biospecdb.qc.qcfilter.QcTestDummyTrue")
    annotator.full_clean()
    annotator.save()

    for data in SpectralData.objects.all():
        assert len(data.get_unrun_annotators()) == 1


@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)  # AUTO_ANNOTATE = True
def test_get_new_unrun_annotators(monkeypatch, qcannotators, mock_data_from_files):
    for data in SpectralData.objects.all():
        assert len(data.get_unrun_annotators()) == 0

    monkeypatch.setattr(settings, "RUN_DEFAULT_ANNOTATORS_WHEN_SAVED", True)

    annotator = QCAnnotator(name="tets", fully_qualified_class_name="biospecdb.qc.qcfilter.QcTestDummyTrue")
    annotator.full_clean()
    annotator.save()

    for data in SpectralData.objects.all():
        assert len(data.get_unrun_annotators()) == 0


def test_management_command_no_annotators(db):
    out = StringIO()
    call_command("run_qc_annotators", stdout=out)
    assert "No annotators exist to annotate." in out.getvalue()


def test_management_command_no_data(qcannotators):
    out = StringIO()
    call_command("run_qc_annotators", stdout=out)
    assert "No SpectralData exists to annotate." in out.getvalue()


def test_management_command(mock_data_from_files, qcannotators):
    for annotation in QCAnnotation.objects.all():
        assert annotation.value is None

    call_command("run_qc_annotators")

    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results


@pytest.mark.parametrize("mock_data_from_files", [True], indirect=True)  # AUTO_ANNOTATE = True
def test_management_command_no_reruns(monkeypatch, qcannotators, mock_data_from_files):
    # Test annotation values are as expected (run when saving mock_data_from_files).
    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results

    # We'll need this later.
    old_QcSum_run = biospecdb.qc.qcfilter.QcSum.run

    # monkeypatch existing annotator class to QcTestDummyTrue.
    monkeypatch.setattr(biospecdb.qc.qcfilter.QcSum, "run", biospecdb.qc.qcfilter.QcTestDummyTrue.run)
    obj = import_string("biospecdb.qc.qcfilter.QcSum")
    assert obj.run(obj, None) is True

    # Note: Using ``subprocess.call`` won't work since the new process re-imports and the
    # patch isn't persisted there. Use ``call_command`` instead.
    call_command("run_qc_annotators")

    # Test that above patch worked.
    for annotation in QCAnnotation.objects.all():
        assert annotation.value == "True"

    # Revert patch.
    monkeypatch.setattr(biospecdb.qc.qcfilter.QcSum, "run", old_QcSum_run)

    # Run again.
    call_command("run_qc_annotators")

    # Test that the patch reversion worked.
    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results

    # Now this is the actual test... (everything above was just a sanity check for the test itself)
    # Re-patch with QcTestDummyTrue
    monkeypatch.setattr(biospecdb.qc.qcfilter.QcSum, "run", biospecdb.qc.qcfilter.QcTestDummyTrue.run)

    # ...and test that ``--no_reruns`` works as annotations != True.
    call_command("run_qc_annotators", "--no_reruns")
    for expected_results, annotation in zip(expected_sum_results, QCAnnotation.objects.all()):
        assert pytest.approx(float(annotation.value)) == expected_results
