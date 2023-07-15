from pathlib import Path

import django.core.files
from django.core.management import call_command
import pytest

from uploader.models import UploadedFile

DATA_PATH = Path(__file__).parent / "data"


@pytest.fixture(scope="function")
def diseases(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'diseases.json')


@pytest.fixture(scope="function")
def instruments(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'instruments.json')


@pytest.fixture(scope="function")
def patients(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'biospecdb/apps/uploader/tests/data/patients.json')


@pytest.fixture(scope="function")
def visits(patients, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'biospecdb/apps/uploader/tests/data/visits.json')


@pytest.fixture(scope="function")
def all_data(db, diseases, django_db_blocker, instruments):
    meta_data_path = (DATA_PATH / "meta_data").with_suffix(UploadedFile.FileFormats.XLSX)
    spectral_file_path = (DATA_PATH / "spectral_data").with_suffix(UploadedFile.FileFormats.XLSX)
    with django_db_blocker.unblock():
        with meta_data_path.open(mode="rb") as meta_data:
            with spectral_file_path.open(mode="rb") as spectral_data:
                data_upload = UploadedFile(meta_data_file=django.core.files.File(meta_data,
                                                                                 name=meta_data_path.name),
                                           spectral_data_file=django.core.files.File(spectral_data,
                                                                                     name=spectral_file_path.name))
                data_upload.clean()
                data_upload.save()
