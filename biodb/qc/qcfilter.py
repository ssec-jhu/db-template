from abc import ABC, abstractmethod

import numpy as np


class QCValidationError(Exception):
    ...


class QcFilter(ABC):
    @abstractmethod
    def run(self, array_data):
        """
            Implement this method to return the actual annotation value(s).

            param: array_data - uploader.models.ArrayData

            Raises QCValidationError.
        """
        ...


class QcSum(QcFilter):
    def run(self, array_data: "ArrayData"):  # noqa: F821
        data = array_data.get_array_data()
        res = np.sum(data.y)
        return res


class QcTestDummyTrue(QcFilter):
    """ For testing purposes only. """
    def run(self, array_data):
        return True


class QcTestDummyFalse(QcFilter):
    """ For testing purposes only. """
    def run(self, array_data):
        return False
