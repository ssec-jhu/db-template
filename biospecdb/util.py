import csv
import enum
import importlib
from io import IOBase
import os
from pathlib import Path

import pandas as pd

from . import __project__  # Keep as relative for templating reasons.


def find_package_location(package=__project__):
    return importlib.util.find_spec(package).submodule_search_locations[0]


def find_repo_location(package=__project__):
    return os.path.abspath(os.path.join(find_package_location(package), os.pardir))


class StrEnum(enum.StrEnum):
    @classmethod
    def list(cls):
        return [x.value for x in cls]


class FileFormats(StrEnum):
    CSV = ".csv"
    XLSX = ".xlsx"

    @classmethod
    def choices(cls):
        return [x.value.replace('.', '') for x in cls]  # Remove '.' for django validator.


def read_raw_data(file_path):
    path = Path(file_path)

    kwargs = dict(true_values=["true", "True", "yes", "Yes"],
                  false_values=["false", "False", "no", "No"],
                  na_values=[' ', '', "unknown", "Unknown", "na", "NA", "n/a", "N/A", "NULL", "null", "None", "none"]
                  )
    # NOTE: The following default na_values are also used:
    # ‘’, ‘  # N/A’, ‘#N/A N/A’, ‘#NA’, ‘-1.#IND’, ‘-1.#QNAN’, ‘-NaN’, ‘-nan’, ‘1.#IND’, ‘1.#QNAN’, ‘<NA>’, ‘N/A’, ‘NA’,
    # ‘NULL’, ‘NaN’, ‘None’, ‘n/a’, ‘nan’, ‘null’.

    if (ext := path.suffix.lower()) == FileFormats.CSV:  # NOTE: ``suffix[1:]`` to strip leading '.'
        data = pd.read_csv(path, **kwargs)
    elif ext == FileFormats.XLSX:
        data = pd.read_excel(path, **kwargs)
    else:
        raise NotImplementedError(f"File ext must be one of {FileFormats.list()} not '{ext}'.")

    return data


def read_meta_data(file_path):
    data = read_raw_data(file_path)

    # Clean.
    # TODO: Raise on null patient_id instead of silently dropping possible data.
    cleaned_data = data.rename(columns=lambda x: x.lower()) \
        .dropna(subset=['patient id']) \
        .set_index('patient id') \
        .fillna('').replace('', None)
    return cleaned_data


def read_spectral_data_table(file_path):
    data = read_raw_data(file_path)

    # Clean.
    # TODO: Raise on null patient id instead of silently dropping possible data.
    cleaned_data = data.rename(columns={"PATIENT ID": "patient id"})
    spec_only = cleaned_data.drop(columns=["patient id"], inplace=False)
    wavelengths = spec_only.columns.tolist()
    specv = spec_only.values.tolist()
    freqs = [wavelengths for i in range(len(specv))]
    return pd.DataFrame({"wavelength": freqs, "intensity": specv}, index=cleaned_data["patient id"])


def spectral_data_to_csv(file, wavelengths, intensities):
    if len(wavelengths) != len(intensities):
        raise ValueError("wavelengths and intensities must be of the same length"
                         " ({len(wavelengths)} != {len(intensities))")

    def write(io):
        writer = csv.writer(io)
        writer.writerow(wavelengths)
        writer.writerow(intensities)

    if isinstance(file, IOBase):
        write(file)
    else:
        with open(file, 'w+', newline='') as f:
            write(f)


def spectral_data_from_csv(filename):
    with open(filename, 'r', newline='') as file:
        reader = csv.reader(file, quoting=csv.QUOTE_NONNUMERIC)
        wavelengths = reader.__next__()
        intensities = reader.__next__()

        if len(wavelengths) != len(intensities):
            raise ValueError("CSV read error. Wavelengths and intensities must be of the same length"
                             " ({len(wavelengths)} != {len(intensities))")

        return wavelengths, intensities


def to_bool(value: str):
    TRUE = ("true", "yes")
    FALSE = ("false", "no")

    if isinstance(value, str):
        if value := value.lower() in TRUE:
            return True
        elif value in FALSE:
            return False
        else:
            raise ValueError(f"Bool aliases are {TRUE}|{FALSE}, not {value}")
    elif isinstance(value, (int, float)):
        return bool(value)
    else:
        raise NotImplementedError
