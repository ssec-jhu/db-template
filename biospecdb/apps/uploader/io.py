from collections import namedtuple
from io import IOBase
import json
from pathlib import Path

import django.core.files
import django.core.files.uploadedfile
from django.core.serializers.json import DjangoJSONEncoder
import pandas as pd
from pandas._libs.parsers import STR_NA_VALUES

from biospecdb.util import StrEnum, to_uuid

SpectralDataTuple = namedtuple("SpectralDataTuple", ["patient_id", "wavelength", "intensity"])


JSON_OPTS = {"indent": ' ', "force_ascii": True}


class DataSchemaError(Exception):
    ...


class FileFormats(StrEnum):
    CSV = ".csv"
    XLSX = ".xlsx"
    JSON = ".json"

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
    elif ext == FileFormats.JSON:
        data = pd.read_json(file, dtype=kwargs["dtype"])
        data.replace(kwargs["true_values"], True, inplace=True)
        data.replace(kwargs["false_values"], False, inplace=True)
        na_values = kwargs["na_values"].copy()
        na_values.extend(list(STR_NA_VALUES))
        data.replace(na_values, None, inplace=True)
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
    """ Read in multiple rows of data returning a pandas.DataFrame.

        This assumes the following format:
        | patient_id | min_lambda | ... | max_lambda |
        | ---------- | ---------- | --- | ---------- |
        |<some UUID> | intensity  | ... | intensity  |
    """
    data = read_raw_data(file, ext=ext)

    # Clean.
    # TODO: Raise on null patient id instead of silently dropping possible data.
    cleaned_data = data.rename(columns={"PATIENT ID": "patient id"})
    spec_only = cleaned_data.drop(columns=["patient id"], inplace=False)
    wavelengths = spec_only.columns.tolist()
    specv = spec_only.values.tolist()
    freqs = [wavelengths for i in range(len(specv))]

    df = pd.DataFrame({"patient_id": [to_uuid(x) for x in cleaned_data["patient id"]],
                       "wavelength": freqs,
                       "intensity": specv})
    df.set_index("patient_id", inplace=True, drop=False)
    return df


def read_single_row_spectral_data_table(file, ext=None):
    """ Read in single row spectral data.

        This assumes the same format as ``read_spectral_data_table`` except that it contains data for only a single
        patient, i.e., just a single row:
        | patient_id | min_lambda | ... | max_lambda |
        | ---------- | ---------- | --- | ---------- |
        |<some UUID> | intensity  | ... | intensity  |
    """

    df = read_spectral_data_table(file, ext=ext)

    if (length := len(df)) != 1:
        raise ValueError(f"The file read should contain only a single row not '{length}'")

    return df.itertuples(index=True, name="SpectralDataTuple").__next__()


def spectral_data_to_json(file, data: SpectralDataTuple, patient_id=None, wavelengths=None, intensities=None):
    """ Convert data to json equivalent to ``json.dumps(SpectralDataTuple._asdict())``.

        Returns json str and/or writes to file.
    """

    if not data:
        assert patient_id is not None
        assert wavelengths is not None
        assert intensities is not None
        data = dict(patient_id=patient_id, wavelength=wavelengths, intensity=intensities)

    if isinstance(data, SpectralDataTuple):
        data = data._asdict()

    kwargs = dict(indent=JSON_OPTS["indent"], ensure_ascii=JSON_OPTS["force_ascii"], cls=DjangoJSONEncoder)
    if file is None:
        return json.dumps(data, **kwargs)

    if isinstance(file, (str, Path)):
        with open(file, mode="w") as fp:
            return json.dump(data, fp, **kwargs)
    else:
        # Note: We assume that this is pointing to the correct section of the file, i.e., the beginning.
        return json.dump(data, file, **kwargs)


def spectral_data_from_json(file):
    """ Read spectral data file and return data SpectralDataTuple instance. """
    # Determine whether file obj (fp) or filename.
    filename = file if isinstance(file, (str, Path)) else file.name
    filename = Path(filename)
    ext = filename.suffix

    if ext != FileFormats.JSON:
        raise ValueError(f"Incorrect file format - expected '{FileFormats.JSON}' but got '{ext}'")

    if isinstance(file, (str, Path)):
        with open(filename, mode="r") as fp:
            data = json.load(fp)
    else:
        # Note: We assume that this is pointing to the correct section of the file, i.e., the beginning.
        data = json.load(file)

    if (fields := set(SpectralDataTuple._fields)) != data.keys():
        raise DataSchemaError(f"Schema error: expected only the fields '{fields}' but got '{data.keys()}'")

    return SpectralDataTuple(**data)


def read_spectral_data(file, ext=None):
    """ General purpose reader to handle multiple file formats returning SpectralDataTuple instance. """
    if ext == FileFormats.JSON:
        return spectral_data_from_json(file)

    return read_single_row_spectral_data_table(file, ext=ext)


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
