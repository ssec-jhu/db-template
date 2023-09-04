from abc import ABC, abstractmethod

import pandas as pd


class QCValidationError(Exception):
    ...


class QcFilter(ABC):

    @abstractmethod
    def run(self, data):
        """
            Raises QCValidationError.
        """
        ...


class QcSum(QcFilter):
    def run(self, data):
        res = pd.DataFrame.sum(data, axis=0)["intensity"]
        return res


class QcTestDummyTrue(QcFilter):
    """ For testing purposes only. """
    def run(self, data):
        return True


class QcTestDummyFalse(QcFilter):
    """ For testing purposes only. """
    def run(self, data):
        return False
