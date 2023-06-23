from django.core.management import call_command
import pytest


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


@pytest.fixture
def visits(patients, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'biospecdb/apps/uploader/tests/data/visits.json')
