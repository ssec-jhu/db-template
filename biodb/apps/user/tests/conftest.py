import pytest
from django.core.management import call_command


@pytest.fixture(scope="function")
def centers(django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "centers")
        call_command("loaddata", "--database=bsr", "centers")
