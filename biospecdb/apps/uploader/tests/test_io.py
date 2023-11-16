import json
from pathlib import Path
import pytest

from django.core.files.base import ContentFile

import uploader.io
from uploader.tests.conftest import DATA_PATH


SPECTRAL_FILE_PATH = (DATA_PATH/"sample")


@pytest.fixture(scope="module")
def json_data():
    filename = SPECTRAL_FILE_PATH.with_suffix(uploader.io.FileFormats.JSONL)
    with open(filename, mode="r") as fp:
        return json.load(fp)


class TestReadSingleRowSpectralDataTable:
    @pytest.mark.parametrize("ext", uploader.io.FileFormats.list())
    def test_read(self, json_data, ext):
        filename = SPECTRAL_FILE_PATH.with_suffix(ext)
        data = uploader.io.read_single_row_spectral_data_table(filename)
        assert str(data.patient_id) == json_data["patient_id"]

    @pytest.mark.parametrize("ext", uploader.io.FileFormats.list())
    def test_multiple_row_exception(self, ext):
        with pytest.raises(ValueError, match="The file read should contain only a single row"):
            uploader.io.read_single_row_spectral_data_table((DATA_PATH/"spectral_data").with_suffix(ext))


class TestSpectralDataFromJson:
    def test_read(self, json_data):
        filename = SPECTRAL_FILE_PATH.with_suffix(uploader.io.FileFormats.JSONL)
        assert uploader.io.spectral_data_from_json(filename) == uploader.io.SpectralData(**json_data)

    def test_spectral_data_from_json_key_validation(self):
        fake_data = ContentFile(json.dumps({"blah": "huh?", "wavelength": [], "something else": 1.0}),
                                name=Path("fake_json").with_suffix(uploader.io.FileFormats.JSONL))
        with pytest.raises(uploader.io.DataSchemaError, match="Schema error:"):
            uploader.io.spectral_data_from_json(fake_data)

    def test_exceptions(self):
        with pytest.raises(ValueError, match="Incorrect file format"):
            uploader.io.spectral_data_from_json("filename_without_an_extension")


class TestSpectralDataToJson:
    def test_data_as_dict(self, json_data):
        json_str = uploader.io.spectral_data_to_json(None, data=json_data)
        assert isinstance(json_str, str)
        assert json.loads(json_str) == json_data

    def test_data_as_dataclass(self, json_data):
        json_str = uploader.io.spectral_data_to_json(None, data=uploader.io.SpectralData(**json_data))
        assert isinstance(json_str, str)
        assert json.loads(json_str) == json_data

    def test_data_as_kwargs(self, json_data):
        json_str = uploader.io.spectral_data_to_json(None, data=None, **json_data)
        assert isinstance(json_str, str)
        assert json.loads(json_str) == json_data

    def test_data_as_filename(self, json_data, tmp_path):
        filename = (Path(tmp_path)/"myjson").with_suffix(uploader.io.FileFormats.JSONL)
        # Write data.
        uploader.io.spectral_data_to_json(filename, json_data)
        # Read data.
        data = uploader.io.spectral_data_from_json(filename)
        assert uploader.io.SpectralData(**json_data) == data

    def test_data_as_fp(self, json_data, tmp_path):
        filename = (Path(tmp_path)/"myjson").with_suffix(uploader.io.FileFormats.JSONL)
        # Write data.
        with filename.open(mode='w') as fp:
            uploader.io.spectral_data_to_json(fp, json_data)
        # Read data.
        data = uploader.io.spectral_data_from_json(filename)
        assert uploader.io.SpectralData(**json_data) == data


class TestReadRawData:
    @pytest.mark.parametrize("ext", uploader.io.FileFormats.list())
    def test_read(self, ext):
        data = uploader.io.read_raw_data((DATA_PATH/"spectral_data").with_suffix(ext))
        assert len(data) == 10

    def test_ext_exception(self):
        with pytest.raises(ValueError, match="When passing an IO stream, ext must be specified"):
            uploader.io.read_raw_data(None, None)

        with pytest.raises(ValueError, match="A path-like or file-like object must be specified"):
            uploader.io.read_raw_data(None, ext=".whatever")

        with pytest.raises(NotImplementedError, match="File ext must be one of"):
            uploader.io.read_raw_data("somefile", ext=".whatever")
