import pytest
from django.core.exceptions import ValidationError
from user.models import Center


@pytest.mark.django_db(databases=["default", "bsr"])
class TestCenter:
    def test_us_center(self):
        center = Center(name="test", country="USA")
        with pytest.raises(ValidationError, match="This repository is not HIPAA compliant"):
            center.full_clean()

    def test_non_us_center(self):
        center = Center(name="test", country="UK")
        center.full_clean()
