import enum
import importlib
import os
from pathlib import Path
from uuid import UUID
import yaml

import boto3
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import numpy as np
import pandas as pd

from . import __project__  # Keep as relative for templating reasons.


def find_package_location(package=__project__):
    return Path(importlib.util.find_spec(package).submodule_search_locations[0])


def find_repo_location(package=__project__):
    return find_package_location(package) / os.pardir


class StrEnum(enum.StrEnum):
    @classmethod
    def list(cls):
        return [x.value for x in cls]


def to_bool(value):
    TRUE = ("true", "yes", True)
    FALSE = ("false", "no", False)

    if value is None or value == '':
        return None

    if isinstance(value, str):
        value = value.lower()

    if value in TRUE:
        return True
    elif value in FALSE:
        return False
    else:
        if isinstance(value, (int, float)):
            raise ValueError(f"int|float casts to bool must have explicit values of 0|1 (inc. their flt equivalents.), "
                             f"not '{value}'")
        else:
            raise ValueError(f"Bool aliases are '{TRUE}|{FALSE}', not '{value}'")


def mock_bulk_spectral_data(path=Path.home(),
                            max_wavelength=4000,
                            min_wavelength=651,
                            n_bins=1798,
                            n_patients=10):
    path = Path(path)
    data = pd.DataFrame(data=np.random.rand(n_patients, n_bins),
                        columns=np.arange(max_wavelength, min_wavelength, (min_wavelength - max_wavelength) / n_bins))
    data.index.name = "PATIENT ID"
    data.index += 1  # Make index 1 based.

    data.to_excel(path / "spectral_data.xlsx")
    data.to_csv(path / "spectral_data.csv")

    return data


def to_uuid(value):
    if isinstance(value, UUID):
        return value

    if value is None:
        return

    def _to_uuid(value):
        # This implementation was copied from django.db.models.UUIDField.to_python.
        input_form = "int" if isinstance(value, int) else "hex"
        return UUID(**{input_form: value})

    try:
        # NOTE: Since string representations of UUIDs containing only numerics are 100% valid, give these precedence by
        # trying to convert directly to UUID instead of converting to int first - try the int route afterward.
        return _to_uuid(value)
    except (AttributeError, ValueError) as error_0:
        if not isinstance(value, str):
            raise

        # Value could be, e.g., '2' or 2.0, so try converting to int.
        try:
            return _to_uuid(int(value))
        except (AttributeError, ValueError) as error_1:
            raise error_1 from error_0


def is_valid_uuid(value):
    # This implementation was copied from django.db.models.UUIDField.to_python.
    if value is not None and not isinstance(value, UUID):
        try:
            to_uuid(value)
        except (AttributeError, ValueError):
            return False
    return True


def lower(value):
    if hasattr(value, "lower"):
        value = value.lower()
    return value


def get_object_or_raise_validation(obj, **kwargs):
    try:
        return obj.objects.get(**kwargs)
    except obj.DoesNotExist:
        raise ValidationError(_("%(name)s does not exist"), params=dict(name=obj.__name__))


def get_field_value(series, obj, field, default=None):
    return series.get(getattr(obj, field).field.verbose_name.lower(), default=default)


def get_aws_secret(arn, region):
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region)
    return client.get_secret_value(SecretId=arn)['SecretString']


def parse_secure_secrets_from_apprunner(apprunner_yaml_file=find_repo_location() / "apprunner.yaml"):
    with open(apprunner_yaml_file) as fp:
        config = yaml.safe_load(fp)
    return {list(d.values())[0]: list(d.values())[1] for d in config["run"]["secrets"]}


def get_aws_secrets(apprunner_yaml_file=find_repo_location() / "apprunner.yaml", region="eu-west-2", export=False):
    secure_secrets = parse_secure_secrets_from_apprunner(apprunner_yaml_file)
    unsecure_secrets = {k: get_aws_secret(v, region=region) for k, v in secure_secrets.items()}

    if export:
        for k, v in unsecure_secrets:
            os.environ[k] = v

    return unsecure_secrets


def print_aws_secrets(apprunner_yaml_file=find_repo_location() / "apprunner.yaml", region="eu-west-2"):
    for k, v in get_aws_secrets(apprunner_yaml_file, region).items():
        print(f"{k}={v}")
