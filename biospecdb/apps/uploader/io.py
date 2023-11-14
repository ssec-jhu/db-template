import dataclasses
from io import IOBase
import json
from pathlib import Path
from uuid import UUID

import django.core.files
import django.core.files.uploadedfile
from django.core.serializers.json import DjangoJSONEncoder
import pandas as pd
from pandas._libs.parsers import STR_NA_VALUES

from biospecdb.util import StrEnum, to_uuid


@dataclasses.dataclass
class SpectralData:
    patient_id: UUID
    wavelength: list
    intensity: list

    def __post_init__(self):
        self.patient_id = to_uuid(self.patient_id)


JSON_OPTS = {"indent": ' ', "force_ascii": True}
TEMP_FILENAME_PREFIX = "__TEMP__"


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
    """ Read data from file-like or path-like object. """
    fp, filename = get_file_info(file)

    # We need an ext to determine which reader to use. If one isn't explicitly passed, obtain from filename.
    if not ext:
        if filename:
            ext = filename.suffix.lower()
        else:
            raise ValueError(f"When passing an IO stream, ext must be specified as one of '{FileFormats.list()}'.")

    # Choose which to actually read from.
    if fp:
        file = fp
    elif filename:
        file = filename
    else:
        raise ValueError("A path-like or file-like object must be specified.")

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
        data.replace(STR_NA_VALUES.union(kwargs['na_values']), pd.NA, inplace=True)
    else:
        raise NotImplementedError(f"File ext must be one of {FileFormats.list()} not '{ext}'.")

    return data


def read_meta_data(file):
    df = read_raw_data(file)

    # Clean.
    cleaned_data = df.rename(columns=lambda x: x.lower())

    # TODO: Raise on null patient_id instead of silently dropping possible data.
    cleaned_data = cleaned_data.dropna(subset=['patient id'])

    # Set index as "patient id" column.
    cleaned_data = cleaned_data.set_index("patient id")

    # Insist on index as UUIDs.
    cleaned_data = cleaned_data.set_index(cleaned_data.index.map(lambda x: to_uuid(x)))

    # Replace na & '' with None via na -> '' -> None
    cleaned_data = cleaned_data.fillna('').replace('', None)

    return cleaned_data


def read_spectral_data_table(file):
    """ Read in multiple rows of data returning a pandas.DataFrame.

        The data to be read in, needs to be of the following table layout:
        Note: Commas need to be present for CSV data.
        Note: The following docstring uses markdown table syntax.
        | patient_id | min_lambda | ... | max_lambda |
        | ---------- | ---------- | --- | ---------- |
        |<some UUID> | intensity  | ... | intensity  |
    """
    df = read_raw_data(file)

    # Clean.
    # TODO: Raise on null patient id instead of silently dropping possible data.
    cleaned_data = df.rename(columns={"PATIENT ID": "patient id"})
    spec_only = cleaned_data.drop(columns=["patient id"], inplace=False)
    wavelengths = spec_only.columns.tolist()
    specv = spec_only.values.tolist()
    freqs = [wavelengths for i in range(len(specv))]

    df = pd.DataFrame({"patient_id": [to_uuid(x) for x in cleaned_data["patient id"]],
                       "wavelength": freqs,
                       "intensity": specv})
    df.set_index("patient_id", inplace=True, drop=False)
    return df


def read_single_row_spectral_data_table(file):
    """ Read in single row spectral data.

        The data to be read in, needs to be of the following table layout:
        Note: Commas need to be present for CSV data.
        Note: The following docstring uses markdown table syntax.
        Note: This is as for ``read_spectral_data_table`` except that it contains data for only a single
        patient, i.e., just a single row:
        | patient_id | min_lambda | ... | max_lambda |
        | ---------- | ---------- | --- | ---------- |
        |<some UUID> | intensity  | ... | intensity  |
    """

    df = read_spectral_data_table(file)

    if (length := len(df)) != 1:
        raise ValueError(f"The file read should contain only a single row not '{length}'")

    data = df.iloc[0]
    return SpectralData(data.patient_id, data.wavelength, data.intensity)


def spectral_data_to_json(file, data: SpectralData, patient_id=None, wavelength=None, intensity=None):
    """ Convert data to json equivalent to ``json.dumps(dataclasses.asdict(SpectralData))``.

        Returns json str and/or writes to file.
    """

    if not data:
        assert patient_id is not None
        assert wavelength is not None
        assert intensity is not None
        data = dict(patient_id=patient_id, wavelength=wavelength, intensity=intensity)

    if isinstance(data, SpectralData):
        data = dataclasses.asdict(data)

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
    """ Read spectral data file and return data SpectralData instance. """
    # Determine whether file obj (fp) or filename.
    fp, filename = get_file_info(file)
    ext = filename.suffix

    if ext != FileFormats.JSON:
        raise ValueError(f"Incorrect file format - expected '{FileFormats.JSON}' but got '{ext}'")

    if fp:
        # Note: We assume that this is pointing to the correct section of the file, i.e., the beginning.
        data = json.load(fp)
    elif filename:
        with open(filename, mode="r") as fp:
            data = json.load(fp)
    else:
        raise ValueError("A path-like or file-like object must be specified.")

    # Check that the json is as expected. This is needed for validation when a user provides json data.
    if (fields := {x.name for x in dataclasses.fields(SpectralData)}) != data.keys():
        raise DataSchemaError(f"Schema error: expected only the fields '{fields}' but got '{data.keys()}'")

    return SpectralData(**data)


def read_spectral_data(file):
    """ General purpose reader to handle multiple file formats returning SpectralData instance. """
    _fp, filename = get_file_info(file)
    ext = filename.suffix

    data = spectral_data_from_json(file) if ext == FileFormats.JSON else read_single_row_spectral_data_table(file)  # noqa:E501
    return data


def get_file_info(file):
    """ The actual file buffer is nested at different levels depending on container class.

        Returns: (fp, Path(filename))
    """
    # Handle base types.
    if file is None:
        return None, None
    elif isinstance(file, str):
        return None, Path(file)
    elif isinstance(file, Path):
        return None, file
    elif isinstance(file, IOBase):
        return file, None

    # Handle Django types.
    if isinstance(file, django.core.files.uploadedfile.TemporaryUploadedFile):
        fp = file.file.file
    elif isinstance(file, django.core.files.File):
        fp = file.file
    else:
        raise NotImplementedError(type(file))

    # The file may have already been read but is still open - so rewind. TODO: potential conflict with #38?
    if hasattr(fp, "closed") and not file.closed and hasattr(fp, "seek"):
        fp.seek(0)
    return fp, Path(file.name)
