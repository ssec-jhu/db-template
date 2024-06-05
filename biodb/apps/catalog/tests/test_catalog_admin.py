import pytest
from catalog.models import Dataset
from django.test import Client


@pytest.mark.django_db(databases=["default", "bsr"])
class TestCatalogAdmin:
    url_root = "/catalog/catalog/dataset/"

    @pytest.mark.parametrize(
        ("user", "expected_resp_code"), (("staffuser", 403), ("cataloguser", 200), ("superuser", 200))
    )
    def test_admin_view_perms_pages(self, request, user, expected_resp_code, mock_data):
        user = request.getfixturevalue(user)
        c = Client()
        c.force_login(user)
        response = c.get(self.url_root, follow=False)
        assert response.status_code == expected_resp_code

    @pytest.mark.parametrize(
        ("user", "expected_resp_code"), (("staffuser", 403), ("cataloguser", 403), ("superuser", 200))
    )
    def test_admin_add_perms_pages(self, request, user, expected_resp_code, mock_data):
        user = request.getfixturevalue(user)
        c = Client()
        c.force_login(user)
        response = c.get(f"{self.url_root}add/", follow=False)
        assert response.status_code == expected_resp_code

    @pytest.mark.parametrize(
        ("user", "expected_resp_code"), (("staffuser", 403), ("cataloguser", 200), ("superuser", 200))
    )
    def test_admin_view_change_perms_pages(
        self, request, user, expected_resp_code, mock_data_from_files, saved_dataset
    ):
        user = request.getfixturevalue(user)
        c = Client()
        c.force_login(user)
        for obj in Dataset.objects.all():
            # Note: cataloguser can view the "change" page but there won't be any update buttons.
            # See ``test_admin_post_change_perms_pages`` below.
            response = c.get(f"{self.url_root}{obj.pk}/change/", follow=False)
            assert response.status_code == expected_resp_code

    @pytest.mark.parametrize("user", ("staffuser", "cataloguser", "superuser"))
    def test_admin_post_change_perms_pages(self, request, user, mock_data_from_files, saved_dataset):
        user = request.getfixturevalue(user)
        c = Client()
        c.force_login(user)
        for obj in Dataset.objects.all():
            response = c.post(f"{self.url_root}{obj.pk}/change/", follow=False)
            assert response.status_code == 403

    @pytest.mark.parametrize(
        ("user", "expected_resp_code"), (("staffuser", 403), ("cataloguser", 403), ("superuser", 200))
    )
    def test_admin_delete_perms_pages(self, request, user, expected_resp_code, mock_data_from_files, saved_dataset):
        user = request.getfixturevalue(user)
        c = Client()
        c.force_login(user)
        for obj in Dataset.objects.all():
            response = c.get(f"{self.url_root}{obj.pk}/delete/", follow=False)
            assert response.status_code == expected_resp_code
