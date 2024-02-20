import pytest

from django.db.utils import IntegrityError

from user.models import Center as UserCenter
from uploader.models import Center as UploaderCenter


@pytest.mark.django_db(databases=["default", "bsr"])
class TestCenters:
    def test_centers_fixture(self, centers):
        ssec_from_user_table = UserCenter.objects.get(name="SSEC")
        ssec_from_uploader_table = UploaderCenter.objects.get(name="SSEC")

        assert ssec_from_user_table.pk == ssec_from_uploader_table.pk
        assert ssec_from_user_table.name == ssec_from_uploader_table.name
        assert ssec_from_user_table.country == ssec_from_uploader_table.country

    def test_validation(self):
        UserCenter.objects.create(name="test", country="nowhere")
        with pytest.raises(IntegrityError, match="UNIQUE constraint failed:"):
            UserCenter.objects.create(name="test", country="nowhere")

    def test_save_replication(self):
        assert not UserCenter.objects.all()
        assert not UploaderCenter.objects.all()

        new_center = UserCenter(name="test", country="nowhere")
        new_center.full_clean()
        new_center.save()

        assert UserCenter.objects.count() == 1
        assert UploaderCenter.objects.count() == 1

        replica_center = UploaderCenter.objects.all()[0]

        assert new_center.pk == replica_center.pk
        assert new_center.name == replica_center.name
        assert new_center.country == replica_center.country

    def test_create_replication(self):
        """ Create doesn't call save()!!! """
        assert not UserCenter.objects.all()
        assert not UploaderCenter.objects.all()

        UserCenter.objects.create(name="test", country="nowhere")
        assert UserCenter.objects.count() == 1
        # Create doesn't call save()!!!
        assert UploaderCenter.objects.count() == 0

    def test_delete_replication(self, centers):
        assert UserCenter.objects.count() == 3
        assert UploaderCenter.objects.count() == 3

        for obj in UserCenter.objects.all():
            obj.delete()

        assert not UserCenter.objects.all()
        assert not UploaderCenter.objects.all()

    def test_bulk_delete_replication(self, centers):
        """ Bulk delete doesn't call delete()!!! """

        assert UserCenter.objects.count() == 3
        assert UploaderCenter.objects.count() == 3

        UserCenter.objects.all().delete()

        assert not UserCenter.objects.all()
        assert UploaderCenter.objects.count() == 3

    def test_equivalence(self):
        user_center = UserCenter(name="test", country="nowhere")
        user_center.full_clean()
        user_center.save()

        uploader_center = UploaderCenter.objects.get(pk=user_center.pk)
        assert user_center == uploader_center
        assert uploader_center == user_center
