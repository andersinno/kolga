import pytest

from scripts.utils.general import (
    camel_case_split,
    get_database_url,
    get_deploy_name,
    get_secret_name,
)


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
        ("stable", "testing"),  # Stable is a special case
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
        ("stable", "testing-secret"),  # Stable is a special case
        ("qa", "testing-qa-secret"),
        ("lizard", "testing-lizard-secret"),
        ("1", "testing-1-secret"),
    ],
)
def test_get_secret_name(track: str, expected: str) -> None:
    assert get_secret_name(track) == expected


def test_get_database_url_stable() -> None:
    url = get_database_url("stable")
    assert url.drivername == "postgres"
    assert url.username == "testuser"
    assert url.password == "testpass"
    assert url.host == "testing-postgres"
    assert url.port == 5432
    assert url.database == "testdb"
