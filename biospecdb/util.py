import enum
import importlib
from io import IOBase
import os
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd

import django.core.files
import django.core.files.uploadedfile

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


def read_raw_data(file, ext=None):
    """
    Read data either from file path or IOStream.

    NOTE: `ext` is ignored when `file` is pathlike.
    """

    if isinstance(file, (IOBase, django.core.files.File)):
        # In this mode the ext must be given as it can't be determined from a file path, since one isn't given.
        if ext:
            ext = ext.lower()
        else:
            raise ValueError(f"When passing an IO stream, ext must be specified as one of '{FileFormats.list()}'.")
    else:
        file = Path(file)
        ext = file.suffix.lower()

    kwargs = dict(true_values=["yes", "Yes"],  # In addition to case-insensitive variants of True.
                  false_values=["no", "No"],  # In addition to case-insensitive variants of False.
                  na_values=[' ', "unknown", "Unknown", "na", "none"],
                  dtype={"Patient ID":  str, "patient id": str, "patient_id": str})
    # NOTE: The patient ID as a str is crucial for converting to UUIDs as floats cannot be safely converted nor is it
    # ok to read in as int as they could be actual UUID str.
    # NOTE: The following default na_values are also used:
    # ‘’, ‘  # N/A’, ‘#N/A N/A’, ‘#NA’, ‘-1.#IND’, ‘-1.#QNAN’, ‘-NaN’, ‘-nan’, ‘1.#IND’, ‘1.#QNAN’, ‘<NA>’, ‘N/A’, ‘NA’,
    # ‘NULL’, ‘NaN’, ‘None’, ‘n/a’, ‘nan’, ‘null’.

    # NOTE: When the file size is > 2.5M Django will chunk and this will need to be handled. See
    # https://github.com/ssec-jhu/biospecdb/issues/38
    if ext == FileFormats.CSV:
        data = pd.read_csv(file, **kwargs)
    elif ext == FileFormats.XLSX:
        data = pd.read_excel(file, **kwargs)
    else:
        raise NotImplementedError(f"File ext must be one of {FileFormats.list()} not '{ext}'.")

    return data


def read_meta_data(file, ext=None):
    data = read_raw_data(file, ext=ext)

    # Clean.
    cleaned_data = data.rename(columns=lambda x: x.lower())

    # TODO: Raise on null patient_id instead of silently dropping possible data.
    cleaned_data = cleaned_data.dropna(subset=['patient id'])

    # Set index as "patient id" column.
    cleaned_data = cleaned_data.set_index("patient id")

    # Insist on index as UUIDs.
    cleaned_data = cleaned_data.set_index(cleaned_data.index.map(lambda x: to_uuid(x)))

    # Replace na & '' with None via na -> '' -> None
    cleaned_data = cleaned_data.fillna('').replace('', None)

    return cleaned_data


def read_spectral_data_table(file, ext=None):
    data = read_raw_data(file, ext=ext)

    # Clean.
    # TODO: Raise on null patient id instead of silently dropping possible data.
    cleaned_data = data.rename(columns={"PATIENT ID": "patient id"})
    spec_only = cleaned_data.drop(columns=["patient id"], inplace=False)
    wavelengths = spec_only.columns.tolist()
    specv = spec_only.values.tolist()
    freqs = [wavelengths for i in range(len(specv))]
    return pd.DataFrame({"wavelength": freqs, "intensity": specv},
                        index=[to_uuid(x) for x in cleaned_data["patient id"]])


def spectral_data_to_csv(file, wavelengths, intensities):
    return pd.DataFrame(dict(intensity=intensities), index=wavelengths).rename_axis("wavelength").to_csv(file)


def spectral_data_from_csv(filename):
    return pd.read_csv(filename)


def to_bool(value):
    TRUE = ("true", "yes", True)
    FALSE = ("false", "no", False)

    if value is None or value == '':
        return None

    if isinstance(value, str):
        value = value.lower()

    if value in TRUE:
        return True
    elif value in FALSE:
        return False
    else:
        if isinstance(value, (int, float)):
            raise ValueError(f"int|float casts to bool must have explicit values of 0|1 (inc. their flt equivalents.), "
                             f"not '{value}'")
        else:
            raise ValueError(f"Bool aliases are '{TRUE}|{FALSE}', not '{value}'")


def mock_bulk_spectral_data(path=Path.home(),
                            max_wavelength=4000,
                            min_wavelength=651,
                            n_bins=1798,
                            n_patients=10):
    path = Path(path)
    data = pd.DataFrame(data=np.random.rand(n_patients, n_bins),
                        columns=np.arange(max_wavelength, min_wavelength, (min_wavelength - max_wavelength) / n_bins))
    data.index.name = "PATIENT ID"
    data.index += 1  # Make index 1 based.

    data.to_excel(path / "spectral_data.xlsx")
    data.to_csv(path / "spectral_data.csv")

    return data


def get_file_info(file_wrapper):
    """ The actual file buffer is nested at different levels depending on container class. """
    if isinstance(file_wrapper, django.core.files.uploadedfile.TemporaryUploadedFile):
        file = file_wrapper.file.file
    elif isinstance(file_wrapper, django.core.files.File):
        file = file_wrapper.file
    else:
        raise NotImplementedError(type(file_wrapper))

    # The file may have already been read but is still open - so rewind. TODO: potential conflict with #38?
    if hasattr(file, "closed") and not file.closed and hasattr(file, "seek"):
        file.seek(0)
    return file, Path(file_wrapper.name).suffix


def to_uuid(value):
    if isinstance(value, UUID):
        return value

    if value is None:
        return

    def _to_uuid(value):
        # This implementation was copied from django.db.models.UUIDField.to_python.
        input_form = "int" if isinstance(value, int) else "hex"
        return UUID(**{input_form: value})

    try:
        # NOTE: Since string representations of UUIDs containing only numerics are 100% valid, give these precedence by
        # trying to convert directly to UUID instead of converting to int first - try the int route afterward.
        return _to_uuid(value)
    except (AttributeError, ValueError) as error_0:
        if not isinstance(value, str):
            raise

        # Value could be, e.g., '2' or 2.0, so try converting to int.
        try:
            return _to_uuid(int(value))
        except (AttributeError, ValueError) as error_1:
            raise error_1 from error_0


def is_valid_uuid(value):
    # This implementation was copied from django.db.models.UUIDField.to_python.
    if value is not None and not isinstance(value, UUID):
        try:
            to_uuid(value)
        except (AttributeError, ValueError):
            False
    return True
