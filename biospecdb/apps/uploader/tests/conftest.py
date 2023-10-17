from pathlib import Path
from uuid import uuid4

from django.conf import settings
import django.core.files
from django.core.management import call_command
from django.test import RequestFactory
from explorer.models import Query
from explorer.tests.factories import UserFactory as ExplorerUserFactory
from factory import Sequence, SubFactory
from factory.django import DjangoModelFactory
import pytest


from biospecdb.util import find_package_location
from uploader.models import UploadedFile, Center
from uploader.forms import DataInputForm
from user.models import Center as UserCenter

DATA_PATH = Path(__file__).parent / "data"


class CenterFactory(DjangoModelFactory):

    class Meta:
        model = UserCenter

    id = uuid4()
    name = Sequence(lambda n: 'name %03d' % n)
    country = Sequence(lambda n: 'country %03d' % n)


class UserFactory(ExplorerUserFactory):
    center = SubFactory(CenterFactory)


class SimpleQueryFactory(DjangoModelFactory):

    class Meta:
        model = Query

    title = Sequence(lambda n: f'My simple query {n}')
    sql = "select * from uploader_spectraldata"
    description = "Stuff"
    connection = settings.EXPLORER_DEFAULT_CONNECTION
    created_by_user = SubFactory(UserFactory)


@pytest.fixture(scope="function")
def django_request(center):
    request = RequestFactory()
    user = UserFactory()
    user.center = UserCenter.objects.get(name="SSEC")
    request.user = user
    return request


@pytest.fixture(scope="function")
def centers(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', "centers")
        call_command("loaddata",  "--database=bsr", "centers")


@pytest.fixture(scope="function")
def center(centers):
    return Center.objects.get(name="SSEC")


@pytest.fixture(scope="function")
def sql_views(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('update_sql_views')


@pytest.fixture(scope="function")
def diseases(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', "--database=bsr", 'diseases.json')


@pytest.fixture(scope="function")
def instruments(django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', "--database=bsr", 'instruments.json')


@pytest.fixture(scope="function")
def patients(django_db_blocker, centers):
    with django_db_blocker.unblock():
        call_command('loaddata', "--database=bsr",
                     str(find_package_location() / 'apps/uploader/tests/data/patients.json'))


@pytest.fixture(scope="function")
def visits(patients, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', "--database=bsr",
                     str(find_package_location() / 'apps/uploader/tests/data/visits.json'))


@pytest.fixture(scope="function")
def qcannotators(db, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', "--database=bsr", 'qcannotators.json')


@pytest.fixture(scope="function")
def mock_data(db, django_db_blocker, centers):
    # NOTE: Since this loads directly to the DB without any validation and thus call to loaddata(), no data files are
    # present. If you need actual spectral data, use ``mock_data_from_files`` below instead.
    with django_db_blocker.unblock():
        call_command('loaddata', "--database=bsr", 'test_data.json')


@pytest.fixture(scope="function")
def mock_data_from_files(request, monkeypatch, db, centers, diseases, django_db_blocker, instruments):
    # patch MEDIA_ROOT
    media_root = request.node.get_closest_marker("media_root")
    if media_root:
        monkeypatch.setattr(settings, "MEDIA_ROOT", media_root.args[0])

    # Turn off auto annotation functionality so that it isn't always being tested.
    auto_annotate = False if getattr(request, "param", None) is None else request.param
    monkeypatch.setattr(settings, "AUTO_ANNOTATE", auto_annotate)

    meta_data_path = (DATA_PATH / "meta_data").with_suffix(UploadedFile.FileFormats.XLSX)
    spectral_file_path = (DATA_PATH / "spectral_data").with_suffix(UploadedFile.FileFormats.XLSX)
    with django_db_blocker.unblock():
        with meta_data_path.open(mode="rb") as meta_data:
            with spectral_file_path.open(mode="rb") as spectral_data:
                data_upload = UploadedFile(meta_data_file=django.core.files.File(meta_data,
                                                                                 name=meta_data_path.name),
                                           spectral_data_file=django.core.files.File(spectral_data,
                                                                                     name=spectral_file_path.name),
                                           center=Center.objects.get(name="SSEC"))
                data_upload.clean()
                data_upload.save()


@pytest.fixture(scope="function")
def mock_data_from_form_and_spectral_file(request, db, data_dict, django_db_blocker, django_request):
    spectral_file_path = (DATA_PATH/"sample").with_suffix(UploadedFile.FileFormats.XLSX)
    with django_db_blocker.unblock():
        with spectral_file_path.open(mode="rb") as spectral_record:
            data_input_form = DataInputForm(
                data=data_dict,
                files={
                    "spectral_data": django.core.files.File(spectral_record, name=spectral_file_path.name)
                },
                request=django_request
            )

            if not request.node.get_closest_marker("dont_validate"):
                assert data_input_form.is_valid(), data_input_form.errors.as_data()

            if not request.node.get_closest_marker("dont_save_to_db"):
                data_input_form.save()
