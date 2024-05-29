import pytest

from django.conf import settings

from biodb.qc.qcmanager import QcManager
from biodb.qc.qcfilter import QcFilter, QCValidationError


class TestFilter(QcFilter):

    def run(self, data):
        return True


class TestQc:
    @pytest.fixture(autouse=True)
    def activate_qcmanager(self, monkeypatch):
        monkeypatch.setattr(settings, "DISABLE_QC_MANAGER", False)

    def test_manager_add_filter(self):
        m = QcManager()
        f = TestFilter()
        m.validator = ('f', f)
        assert m.validators['f'] == f

    def test_manager_add_filters(self):
        m = QcManager()
        f = TestFilter()
        m.validator = ('f', f)
        m.validator = ('g', f)
        m.validator = ('h', f)

        assert len(m.validators) == 3

    def test_run_validations(self):
        m = QcManager()
        m.validator = ('f', TestFilter())
        m.validator = ('g', TestFilter())

        val = m.validate(None)
        assert val['f'] is True
        assert len(val) == 2

    def test_validation_returns_null_on_exception(self):
        m = QcManager()

        f = TestFilter()
        def raise_on_val(*args, **kwargs):
            raise QCValidationError('error')
        f.run = raise_on_val  # Monkey patch TestFilter.run.
        with pytest.raises(QCValidationError):
            f.run(None)

        m.validator = ('f', f)
        val = m.validate(None)
        assert val['f'] is None
