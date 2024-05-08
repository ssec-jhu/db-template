from abc import ABC, abstractmethod

import numpy as np


class QCValidationError(Exception):
    ...


class QcFilter(ABC):
    @abstractmethod
    def run(self, spectral_data):
        """
            Implement this method to return the actual annotation value(s).

            param: spectral_data - uploader.models.SpectralData

            Raises QCValidationError.
        """
        ...


class QcSum(QcFilter):
    def run(self, spectral_data: "SpectralData"):  # noqa: F821
        data = spectral_data.get_spectral_data()
        res = np.sum(data.intensity)
        return res


class QcTestDummyTrue(QcFilter):
    """ For testing purposes only. """
    def run(self, spectral_data):
        return True


class QcTestDummyFalse(QcFilter):
    """ For testing purposes only. """
    def run(self, spectral_data):
        return False
