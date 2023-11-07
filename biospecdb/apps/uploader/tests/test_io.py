import json
import pytest

import uploader.io
from uploader.tests.conftest import DATA_PATH


SPECTRAL_FILE_PATH = (DATA_PATH/"sample")


@pytest.fixture()
def json_data():
    filename = SPECTRAL_FILE_PATH.with_suffix(uploader.io.FileFormats.JSON)
    with open(filename, mode="r") as fp:
        return json.load(fp)


@pytest.mark.parametrize("ext", (uploader.io.FileFormats.CSV, uploader.io.FileFormats.XLSX))
def test_read_single_row_spectral_data_table(json_data, ext):
    filename = SPECTRAL_FILE_PATH.with_suffix(ext)
    data = uploader.io.read_single_row_spectral_data_table(filename)
    assert str(data.patient_id) == json_data["patient_id"]


def test_spectral_data_from_json(json_data):
    filename = SPECTRAL_FILE_PATH.with_suffix(uploader.io.FileFormats.JSON)
    assert uploader.io.spectral_data_from_json(filename) == uploader.io.SpectralData(**json_data)


def test_spectral_data_as_dict_to_json(json_data):
    json_str = uploader.io.spectral_data_to_json(None, data=json_data)
    assert isinstance(json_str, str)
    assert json.loads(json_str) == json_data


def test_spectral_data_as_dataclass_to_json(json_data):
    json_str = uploader.io.spectral_data_to_json(None, data=uploader.io.SpectralData(**json_data))
    assert isinstance(json_str, str)
    assert json.loads(json_str) == json_data


def test_spectral_data_as_kwargs_to_json(json_data):
    json_str = uploader.io.spectral_data_to_json(None, data=None, **json_data)
    assert isinstance(json_str, str)
    assert json.loads(json_str) == json_data
