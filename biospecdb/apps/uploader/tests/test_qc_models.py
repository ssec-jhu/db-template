import pytest
from django.core.exceptions import ValidationError

from uploader.models import QCAnnotator


def test_qcannotators_django_fixture(qcannotators):
    annotators = QCAnnotator.objects.all()
    assert len(annotators) == 1
    assert annotators[0].name == "sum"


def test_qualified_class_name_validator(qcannotators):
    with pytest.raises(ValidationError):
        QCAnnotator(name="fail", qualified_class_name=1).full_clean()

    QCAnnotator(name="fail", qualified_class_name="biospecdb.qc.qcfilter.QcSum").full_clean()

    with pytest.raises(ValidationError):
        QCAnnotator(name="fail", qualified_class_name=1).full_clean()
