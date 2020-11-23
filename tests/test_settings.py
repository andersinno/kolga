import os
from random import sample
from string import ascii_lowercase
from typing import Optional

import pytest

from kolga.settings import settings


def fake_track(invalid_value: str) -> str:
    ret = invalid_value
    n_chars = len(invalid_value) if invalid_value else 8

    while ret == invalid_value:
        ret = "".join(sample(ascii_lowercase, n_chars))

    return ret


def kubeconfig_key(track: Optional[str] = None) -> str:
    track_postfix = f"_{track.upper()}" if track is not None else ""
    return f"KUBECONFIG{track_postfix}"


@pytest.mark.parametrize(  # type: ignore
    "track, is_track_present, expected_variable",
    [
        ("", True, "KUBECONFIG"),
        ("stable", True, "KUBECONFIG_STABLE"),
        ("review", False, "KUBECONFIG"),
    ],
)
def test_setup_kubeconfig_with_track(
    track: str, is_track_present: bool, expected_variable: str
) -> None:
    os.environ.update(
        {
            kubeconfig_key(): "Value from fall-back KUBECONFIG",
            kubeconfig_key(fake_track(track)): "A totally wrong KUBECONFIG",
        }
    )

    if is_track_present:
        os.environ[kubeconfig_key(track)] = "Value from track-specific KUBECONFIG"

    expected_value = os.environ[expected_variable]

    assert settings.setup_kubeconfig(track) == (expected_value, expected_variable)
    assert settings.KUBECONFIG == os.environ["KUBECONFIG"] == expected_value


def test_setup_kubeconfig_raw() -> None:
    os.environ.update({"KUBECONFIG_RAW": "This value is from KUBECONFIG_RAW"})

    value, key = settings.setup_kubeconfig("fake_track")

    result = open(value, "r").read()

    assert key == "KUBECONFIG_RAW"
    assert "This value is from KUBECONFIG_RAW" == result


# KUBECONFIG_RAW is available but empty. Setup should fall back to KUBECONFIG
def test_setup_kubeconfig_raw_empty() -> None:
    os.environ.update({"KUBECONFIG_RAW": "", "KUBECONFIG": "Value from KUBECONFIG"})

    value, key = settings.setup_kubeconfig("fake_track")

    assert key == "KUBECONFIG"
    assert value == "Value from KUBECONFIG"


def test_setup_kubeconfig_raw_with_track() -> None:
    os.environ.update(
        {
            "KUBECONFIG_RAW": "This value is from KUBECONFIG_RAW",
            "KUBECONFIG_RAW_STABLE": "This value is from KUBECONFIG_RAW_STABLE",
        }
    )

    value, key = settings.setup_kubeconfig("STABLE")

    assert key == "KUBECONFIG_RAW_STABLE"
