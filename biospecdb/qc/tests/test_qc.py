import pytest

from biospecdb.qc.qcmanager import QcManager
from biospecdb.qc.qcfilter import QcFilter, QCValidationError


class TestFilter(QcFilter):

    def validate(self, symptoms, sample):
        return True


class TestQc:

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

        val = m.validate(None, None)
        assert val['f'] is True
        assert len(val) == 2

    def test_validation_returns_null_on_exception(self):
        m = QcManager()

        f = TestFilter()
        def raise_on_val(x, y):
            raise QCValidationError('error')
        f.validate = raise_on_val  # Monkey patch TestFilter.validate.
        with pytest.raises(QCValidationError):
            f.validate(None, None)

        m.validator = ('f', f)
        val = m.validate(None, None)
        assert val['f'] is None
