import pytest

from django.contrib.auth import get_user_model
from django.core.management import call_command

from catalog.models import Dataset
from uploader.tests.conftest import bio_sample_types, centers, instruments, mock_data_from_files, observables, \
    SimpleQueryFactory, array_measurement_types, sql_views, mock_data  # noqa: F401
from user.models import Center as UserCenter


User = get_user_model()


@pytest.fixture(scope="function")
def queries(django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "queries")


@pytest.fixture()
def staffuser(centers):  # noqa: F811
    return User.objects.create(username="staff",
                               email="staff@jhu.edu",
                               password="secret",
                               center=UserCenter.objects.get(name="JHU"),
                               is_staff=True,
                               is_superuser=False)


@pytest.fixture()
def cataloguser(centers):  # noqa: F811
    return User.objects.create(username="analyst",
                               email="analyst@jhu.edu",
                               password="secret",
                               center=UserCenter.objects.get(name="JHU"),
                               is_staff=True,
                               is_superuser=False,
                               is_catalogviewer=True)


@pytest.fixture()
def superuser(centers):  # noqa: F811
    return User.objects.create(username="admin",
                               email="admin@jhu.edu",
                               password="secret",
                               center=UserCenter.objects.get(name="JHU"),
                               is_staff=True,
                               is_superuser=True)


@pytest.fixture
def query(mock_data_from_files, sql_views):  # noqa: F811
    q = SimpleQueryFactory(sql="select * from flat_view",
                           title="clean_test",
                           description="something to test")
    q.save()
    return q


@pytest.fixture
def saved_dataset(query):  # noqa: F811
    dataset = Dataset(query=query, version="2023.0.0")
    dataset.full_clean()
    dataset.save()
    return dataset
