import logging

from django.conf import settings

from biospecdb.qc.qcfilter import QcFilter, QCValidationError
from uploader.models import SpectralData

log = logging.getLogger()


class QcManager:

    def __init__(self):
        if settings.DISABLE_QC_MANAGER:
            # Disable this class for now as #69 made it obsolete, however, there's a very good chance it will be needed
            # when implementing background tasks for https://github.com/rispadd/biospecdb/pull/77.
            raise NotImplementedError()

        self._validators = {}

    @property
    def validators(self):
        return self._validators

    @validators.setter
    def validator(self, value) -> None:  # NOTE: validator vs validatorS is intentional.
        name, filter = value

        if not isinstance(filter, QcFilter):
            raise TypeError(f"QC validators must be of type '{QcFilter.__qualname__}' not '{type(filter)}'")

        # Don't clobber existing filters, require unique names.
        if self.validators.get(name):
            raise KeyError(f"'{name}' already exists - filter/validator names must be unique.")

        self._validators[name] = filter

    def validate(self, data: SpectralData) -> dict:
        results = {}
        for name, filter in self.validators.items():
            try:
                results[name] = filter.run(data)
            except QCValidationError as error:
                log.warning(f"The QC validator '{name}' failed: '{error}'")
                results[name] = None

        return results
