import json
from pathlib import Path
import pytest

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import storages

import uploader.io
from uploader.tests.conftest import DATA_PATH


ARRAY_FILE_PATH = (DATA_PATH/"sample")


@pytest.fixture(scope="module")
def json_data():
    filename = ARRAY_FILE_PATH.with_suffix(uploader.io.FileFormats.JSONL)
    with open(filename, mode="r") as fp:
        return json.load(fp)


class TestReadSingleRowArrayDataTable:
    @pytest.mark.parametrize("ext", uploader.io.FileFormats.list())
    def test_read(self, json_data, ext):
        filename = ARRAY_FILE_PATH.with_suffix(ext)
        data = uploader.io.read_single_row_array_data_table(filename)
        assert str(data.patient_id) == json_data["patient_id"]

    @pytest.mark.parametrize("ext", uploader.io.FileFormats.list())
    def test_multiple_row_exception(self, ext):
        with pytest.raises(ValueError, match="The file read should contain only a single row"):
            uploader.io.read_single_row_array_data_table((DATA_PATH/"array_data").with_suffix(ext),
                                                            index_column=settings.BULK_UPLOAD_INDEX_COLUMN_NAME)


class TestArrayDataFromJson:
    def test_read(self, json_data):
        filename = ARRAY_FILE_PATH.with_suffix(uploader.io.FileFormats.JSONL)
        assert uploader.io.array_data_from_json(filename) == uploader.io.ArrayData(**json_data)

    def test_array_data_from_json_key_validation(self):
        fake_data = ContentFile(json.dumps({"blah": "huh?", "x": [], "something else": 1.0}),
                                name=Path("fake_json").with_suffix(uploader.io.FileFormats.JSONL))
        with pytest.raises(uploader.io.DataSchemaError, match="Schema error:"):
            uploader.io.array_data_from_json(fake_data)

    def test_exceptions(self):
        with pytest.raises(ValueError, match="Incorrect file format"):
            uploader.io.array_data_from_json("filename_without_an_extension")


class TestArrayDataToJson:
    def test_data_as_dict(self, json_data):
        json_str = uploader.io.array_data_to_json(None, data=json_data)
        assert isinstance(json_str, str)
        assert json.loads(json_str) == json_data

    def test_data_as_dataclass(self, json_data):
        json_str = uploader.io.array_data_to_json(None, data=uploader.io.ArrayData(**json_data))
        assert isinstance(json_str, str)
        assert json.loads(json_str) == json_data

    def test_data_as_kwargs(self, json_data):
        json_str = uploader.io.array_data_to_json(None, data=None, **json_data)
        assert isinstance(json_str, str)
        assert json.loads(json_str) == json_data

    def test_data_as_filename(self, json_data):
        filename = Path("myjson").with_suffix(uploader.io.FileFormats.JSONL)
        # Write data.
        filename = uploader.io.array_data_to_json(filename, json_data)
        # Read data.
        data = uploader.io.array_data_from_json(filename)
        assert uploader.io.ArrayData(**json_data) == data

    def test_data_as_fp(self, json_data):
        filename = Path("myjson").with_suffix(uploader.io.FileFormats.JSONL)
        # Write data.
        with storages["default"].open(filename, mode='w') as fp:
            uploader.io.array_data_to_json(fp, json_data)
        # Read data.
        data = uploader.io.array_data_from_json(filename)
        assert uploader.io.ArrayData(**json_data) == data


class TestReadRawData:
    @pytest.mark.parametrize("ext", uploader.io.FileFormats.list())
    def test_read(self, ext):
        data = uploader.io._read_raw_data((DATA_PATH / "array_data").with_suffix(ext))
        assert len(data) == 10

    def test_ext_exception(self):
        with pytest.raises(ValueError, match="When passing an IO stream, ext must be specified"):
            uploader.io._read_raw_data(None, None)

        with pytest.raises(ValueError, match="A path-like or file-like object must be specified"):
            uploader.io._read_raw_data(None, ext=".whatever")

        with pytest.raises(NotImplementedError, match="File ext must be one of"):
            uploader.io._read_raw_data("somefile", ext=".whatever")
