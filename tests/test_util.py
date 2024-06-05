from uuid import uuid4

import pytest

from biodb import __project__, __version__
from biodb.util import find_package_location, find_repo_location, is_valid_uuid, to_bool, to_uuid


def test_find_repo_location():
    repo_path = find_repo_location()
    assert repo_path
    assert (repo_path / __project__).exists()


def test_find_package_location():
    pkg_path = find_package_location()
    assert pkg_path
    assert pkg_path.exists()
    assert pkg_path.is_dir()
    assert pkg_path.name == __project__


def test_version_file():
    pkg_path = find_package_location()
    assert pkg_path.exists()
    version_file = pkg_path / "_version.py"
    assert version_file.exists()


def test_version():
    assert __version__


def test_project():
    assert __project__


def test_to_bool_exceptions():
    with pytest.raises(ValueError, match="int|float casts to bool must have explicit value"):
        to_bool(3.14)

    with pytest.raises(ValueError, match="Bool aliases are"):
        to_bool([])


def test_is_valid_uuid():
    assert is_valid_uuid(None)
    assert is_valid_uuid(uuid4())
    assert is_valid_uuid(1)
    assert is_valid_uuid("1")
    assert not is_valid_uuid("this is not a uuid")
    assert not is_valid_uuid([])


def test_to_uuid():
    assert to_uuid(None) is None

    with pytest.raises(ValueError):
        to_uuid("this is not a uuid")

    id = uuid4()
    assert to_uuid(id) is id
