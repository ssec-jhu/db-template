import pytest

from django.contrib.admin.sites import AdminSite

from uploader.tests.conftest import patients  # noqa: F401
from uploader.models import Patient, Center as UploaderCenter
from user.models import Center as UserCenter
from user.admin import CenterAdmin


@pytest.mark.django_db(databases=["default", "bsr"])
class TestCenterAdmin:
    @pytest.fixture(scope="class")
    def site(self):
        return CenterAdmin(model=UserCenter, admin_site=AdminSite())

    def test_site(self, site):
        site.save_model(obj=UserCenter(name="test", country="nowhere"), request=None, form=None, change=None)

    def test_patient_count(self, centers, site, patients):  # noqa: F811
        for center in UserCenter.objects.all():
            n_patients = len(Patient.objects.filter(center=UploaderCenter.objects.get(pk=center.pk)))
            assert site.patient_count(center) == n_patients
