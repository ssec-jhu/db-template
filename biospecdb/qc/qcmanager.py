import logging

from biospecdb.qc.qcfilter import QcFilter, QCValidationError
from uploader.models import BioSample
from uploader.models import Patient as Symptoms

log = logging.getLogger()


class QcManager:

    def __init__(self):
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

    def validate(self, symptoms: Symptoms, sample: BioSample) -> dict:
        results = {}
        for name, filter in self.validators.items():
            try:
                results[name] = filter.validate(symptoms, sample)
            except QCValidationError as error:
                log.warning(f"The QC validator '{name}' failed: '{error}'")
                results[name] = None

        return results
