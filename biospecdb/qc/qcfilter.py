from abc import ABC, abstractmethod

import pandas as pd


class QCValidationError(Exception):
    ...


class QcFilter(ABC):

    @abstractmethod
    def run(self, data) -> bool:
        """
            Raises QCValidationError.
        """
        ...


class QcSum(QcFilter):
    def run(self, data) -> bool:
        return pd.DataFrame.sum(data)
