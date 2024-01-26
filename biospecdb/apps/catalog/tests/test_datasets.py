import json
import os.path
from pathlib import Path
import zipfile

import pytest

from biospecdb import __version__
from catalog.models import Dataset
from explorer.models import Query
from uploader.models import SpectralData


@pytest.mark.django_db(databases=["default", "bsr"])
class TestDataset:

    def test_query_fixture(self, queries):
        assert Query.objects.count() == 1

    def test_clean(self, query):
        assert query.title
        assert query.description
        assert query.sql
        version = "2023.0.0"

        dataset = Dataset(query=query,
                          version=version,
                          )
        dataset.full_clean()

        assert dataset.name == query.title
        assert dataset.description == query.description
        assert dataset.sql == query.sql
        assert dataset.app_version == __version__

    def test_save(self, saved_dataset):
        assert Dataset.objects.count() == 1

    def test_checksum(self, saved_dataset):
        checksum = saved_dataset.compute_checksum()
        assert checksum == saved_dataset.compute_checksum()
        assert saved_dataset.sha256 == checksum

    def test_files(self, saved_dataset):
        file_ext = saved_dataset.get_exporter().file_extension

        with saved_dataset.file.open() as fp:
            with zipfile.ZipFile(fp) as z:
                namelist = z.namelist()
                namelist.remove(str(Path(saved_dataset.name).with_suffix(file_ext)))
                namelist.remove("INFO.json")
                data_dir = Path(SpectralData.UPLOAD_DIR)
                for file in namelist:
                    assert Path(file).parent == data_dir

    def test_info_file(self, saved_dataset):
        with saved_dataset.file.open() as fp:
            with zipfile.ZipFile(fp) as z:
                with z.open("INFO.json") as info_fp:
                    expected_meta_info = json.load(info_fp)
                    expected_meta_info.pop("timestamp")

                    meta_info = saved_dataset.meta_info()
                    meta_info.pop("timestamp")

                    assert meta_info == expected_meta_info

    def test_deletion(self, saved_dataset):
        assert Dataset.objects.get(pk=saved_dataset.pk)
        assert os.path.exists(saved_dataset.file.name)
        saved_dataset.delete()
        assert not Dataset.objects.count()
        assert not os.path.exists(saved_dataset.file.name)
