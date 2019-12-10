import os
from random import sample
from string import ascii_lowercase

import pytest

from scripts.settings import settings


def fake_track(invalid_value: str) -> str:
    ret = invalid_value
    n_chars = len(invalid_value) if invalid_value else 8

    while ret == invalid_value:
        ret = "".join(sample(ascii_lowercase, n_chars))

    return ret


@pytest.mark.parametrize(  # type: ignore
    "track, expected_variable",
    [(None, "KUBECONFIG"), ("", "KUBECONFIG"), ("stable", "KUBECONFIG_stable")],
)
def really_test_setup_kubeconfig_with_track(track: str, expected_variable: str) -> None:
    os.environ.update(
        {
            "KUBECONFIG": "Value from fall-back KUBECONFIG",
            f"KUBECONFIG_{fake_track(track)}": "A totally wrong KUBECONFIG",
            **(
                {f"KUBECONFIG_{track}": "Value from track-specific KUBECONFIG"}
                if track
                else {}
            ),
        },
    )
    expected_value = os.environ[expected_variable]

    assert settings.setup_kubeconfig(track) == (expected_value, expected_variable)
    assert settings.KUBECONFIG == os.environ["KUBECONFIG"] == expected_value
