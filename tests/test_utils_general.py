import os
from uuid import uuid4

import pytest

from scripts.utils.general import (
    camel_case_split,
    get_database_url,
    get_deploy_name,
    get_environment_vars_by_prefix,
    get_secret_name,
)

DEFAULT_TRACK = os.environ.get("DEFAULT_TRACK", "stable")


@pytest.mark.parametrize(  # type: ignore
    "value, expected",
    [
        ("lowerUpper", "Upper"),  # Not camel case
        ("UpperUpper", "Upper upper"),  # Normal camel case
        ("UPPERLower", "Upper lower"),  # All upper camel case, bad camel case
        ("snake_case", ""),
    ],
)
def test_camel_case_split(value: str, expected: str) -> None:
    assert camel_case_split(value) == expected


@pytest.mark.parametrize(  # type: ignore
    "track, expected",
    [
        (DEFAULT_TRACK, "testing"),  # DEFAULT_TRACK is a special case
        ("qa", "testing-qa"),
        ("lizard", "testing-lizard"),
        ("1", "testing-1"),
    ],
)
def test_get_deploy_name(track: str, expected: str) -> None:
    assert get_deploy_name(track) == expected


@pytest.mark.parametrize(  # type: ignore
    "track, expected",
    [
        (DEFAULT_TRACK, "testing-secret"),  # DEFAULT_TRACK is a special case
        ("qa", "testing-qa-secret"),
        ("lizard", "testing-lizard-secret"),
        ("1", "testing-1-secret"),
    ],
)
def test_get_secret_name(track: str, expected: str) -> None:
    assert get_secret_name(track) == expected


def test_get_database_url_stable() -> None:
    url = get_database_url(DEFAULT_TRACK)
    assert url
    assert url.drivername == "postgresql"
    assert url.username == "testuser"
    assert url.password == "testpass"
    assert url.host == "testing-db-postgresql"
    assert url.port == 5432
    assert url.database == "testdb"


def test_get_environment_vars_by_prefix() -> None:
    prefix = f"TEST_{str(uuid4())}_SECRET_"

    env_vars = {f"{prefix}PASSWORD": "pass", f"{prefix}LIZARD": "-1"}
    secrets = {f"PASSWORD": "pass", f"LIZARD": "-1"}

    for key, secret in env_vars.items():
        os.environ[key] = secret

    assert get_environment_vars_by_prefix(prefix) == secrets
