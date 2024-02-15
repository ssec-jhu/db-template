import json
import pytest

from django.db import DatabaseError
from django.test import Client

from health_check.db.models import TestModel


@pytest.mark.django_db(databases=["default", "bsr"])
class TestHealthCheck:
    @pytest.fixture
    def sabotage_db(self, monkeypatch):
        def save(*args, **kwargs):
            raise DatabaseError("Nice try")

        # Monkeypatch health_check's TestModel to raise when testing a DB write.
        monkeypatch.setattr(TestModel, "save", save)

    @pytest.mark.parametrize("method", ("get", "head"))
    def test_healthz(self, method):
        c = Client()
        response = getattr(c, method)("/healthz/")
        assert response.status_code == 200

    @pytest.mark.parametrize("method", ("get", "head"))
    def test_fail(self, sabotage_db, method):
        c = Client()
        response = getattr(c, method)("/healthz/")
        assert response.status_code == 500

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
