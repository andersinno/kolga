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
