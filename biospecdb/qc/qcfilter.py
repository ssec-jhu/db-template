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
    def run(self, data) -> bool:
        res = pd.DataFrame.sum(data, axis=0)["intensity"]
        return res
