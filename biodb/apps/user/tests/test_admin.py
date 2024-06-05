import pytest
from django.contrib.admin.sites import AdminSite
from uploader.models import Center as UploaderCenter
from uploader.models import Patient
from uploader.tests.conftest import patients  # noqa: F401
from user.admin import CenterAdmin
from user.models import Center as UserCenter


@pytest.mark.django_db(databases=["default", "bsr"])
class TestCenterAdmin:
    @pytest.fixture(scope="class")
    def site(self):
        return CenterAdmin(model=UserCenter, admin_site=AdminSite())

    def test_site(self, site):
        site.save_model(obj=UserCenter(name="test", country="nowhere"), request=None, form=None, change=None)

    def test_patient_count(self, centers, site, patients):  # noqa: F811
        for center in UserCenter.objects.all():
            n_patients = Patient.objects.filter(center=UploaderCenter.objects.get(pk=center.pk)).count()
            assert site.patient_count(center) == n_patients
