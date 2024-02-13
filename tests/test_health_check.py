import json
import pytest

from django.test import Client


@pytest.mark.django_db(databases=["default", "bsr"])
class TestHealthCheck:
    def test_healthz(self):
        c = Client()
        response = c.get("/healthz/")
        assert response.status_code == 200

    @pytest.mark.parametrize(("url", "header"), (("/healthz/?format=json", None),
                                                 ("/healthz/", {"accept": "application/json"})))
    def test_healthz_json(self, url, header):
        c = Client()
        response = c.get(url, headers=header)

        assert response.status_code == 200

        content = json.loads(response.content)

        # There should be an entry for each of the installed checks:
        assert len(content) == 4
        assert "Cache backend: default" in content
        assert "DatabaseBackend" in content
        assert "DefaultFileStorageHealthCheck" in content
        assert "MigrationsHealthCheck" in content

        for x in content.values():
            assert x.strip().lower() == "working"
