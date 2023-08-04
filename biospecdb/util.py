import enum
import importlib
from io import IOBase
import os
from pathlib import Path

import numpy as np
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


def read_raw_data(file, ext=None):
    """
    Read data either from file path or IOStream.

    NOTE: `ext` is ignored when `file` is pathlike.
    """

    if isinstance(file, IOBase):
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
                  na_values=[' ', "unknown", "Unknown", "na", "none"]
                  )
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

def populate_meta_data(form):
    # Create a dictionary from the cleaned form data
    data = {
        'patient_id': form['patient_id'],
        'Covid_RT_qPCR': form['Covid_RT_qPCR'],
        'Ct_gene_N': form['Ct_gene_N'],
        'Ct_gene_ORF1ab': form['Ct_gene_ORF1ab'],
        'gender': form['gender'],
        'patient_age': form['patient_age'],
        'days_symptomatic': form['days_symptomatic'],
        'fever': form['fever'],
        'dyspnoea': form['dyspnoea'],
        'oxygen_saturation_lt_95': form['oxygen_saturation_lt_95'],
        'cough': form['cough'],
        'coryza': form['coryza'],
        'odinophagy': form['odinophagy'],
        'diarrhea': form['diarrhea'],
        'nausea': form['nausea'],
        'headache': form['headache'],
        'weakness': form['weakness'],
        'anosmia': form['anosmia'],
        'myalgia': form['myalgia'],
        'lack_of_appetite': form['lack_of_appetite'],
        'vomiting': form['vomiting'],
        'suspicious_contact': form['suspicious_contact'],
        'chronic_pulmonary': form['chronic_pulmonary'],
        'cardiovascular_disease': form['cardiovascular_disease'],
        'diabetes': form['diabetes'],
        'chronic_or_neuromuscular': form['chronic_or_neuromuscular'],
        'spectra_measurement': form['spectra_measurement'],
        'spectrometer': form['spectrometer'],
        'atr_crystal': form['atr_crystal'],
        'acquisition_time': form['acquisition_time'],
        'n_coadditions': form['n_coadditions'],
        'resolution': form['resolution'],
        'sample_type': form['sample_type'],
        'sample_processing': form['sample_processing'],
        'freezing_temp': form['freezing_temp'],
        'thawing_time': form['thawing_time'],
    }
    
    # Convert the dictionary to a Pandas DataFrame
    df = pd.DataFrame([data])

    cleaned_data = df.rename(columns=lambda x: x.lower()) \
        .dropna(subset=['patient_id']) \
        .set_index('patient_id') \
        .fillna('').replace('', None)
    
    return cleaned_data

def read_meta_data(file, ext=None):
    data = read_raw_data(file, ext=ext)

    # Clean.
    # TODO: Raise on null patient_id instead of silently dropping possible data.
    cleaned_data = data.rename(columns=lambda x: x.lower()) \
        .dropna(subset=['patient id']) \
        .set_index('patient id') \
        .fillna('').replace('', None)
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
    return pd.DataFrame({"wavelength": freqs, "intensity": specv}, index=cleaned_data["patient id"])


def spectral_data_to_csv(file, wavelengths, intensities):
    return pd.DataFrame(dict(intensity=intensities), index=wavelengths).rename_axis("wavelength").to_csv(file)


def spectral_data_from_csv(filename):
    return pd.read_csv(filename)


def to_bool(value: str):
    TRUE = ("true", "yes")
    FALSE = ("false", "no")

    if isinstance(value, str):
        value = value.lower()
        if value in TRUE:
            return True
        elif value in FALSE:
            return False
        else:
            raise ValueError(f"Bool aliases are '{TRUE}|{FALSE}', not '{value}'")
    elif isinstance(value, (int, float)):
        return bool(value)
    else:
        raise NotImplementedError


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
