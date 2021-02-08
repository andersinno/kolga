import json
import os
import tempfile
from pathlib import Path
from random import sample
from string import ascii_lowercase
from typing import Any, Dict, Optional, Type
from unittest import mock

import pytest

from kolga.hooks.plugins import PluginBase
from kolga.settings import GitHubActionsMapper, settings


def fake_track(invalid_value: str) -> str:
    ret = invalid_value
    n_chars = len(invalid_value) if invalid_value else 8

    while ret == invalid_value:
        ret = "".join(sample(ascii_lowercase, n_chars))

    return ret


def kubeconfig_key(track: Optional[str] = None) -> str:
    track_postfix = f"_{track.upper()}" if track is not None else ""
    return f"KUBECONFIG{track_postfix}"


@pytest.mark.parametrize(
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


@mock.patch.dict("os.environ", {"TEST_PLUGIN_VARIABLE": "odins_raven"})
def test_load_unload_plugins(test_plugin: Type[PluginBase]) -> None:
    assert settings._load_plugin(plugin=test_plugin)[0] is True
    assert settings._unload_plugin(plugin=test_plugin)


@mock.patch.dict("os.environ", {"GITHUB_EVENT_NAME": "pull_request"})
def test_gh_event_data_set() -> None:
    event_data: Dict[Any, Any] = {
        "action": "opened",
        "number": 2,
        "pull_request": {
            "url": "https://api.github.com/repos/Codertocat/Hello-World/pulls/2",
            "number": 2,
            "title": "Update the README with new information.",
        },
    }

    gh_mapper = GitHubActionsMapper()

    with tempfile.NamedTemporaryFile() as f:
        encoded_string = str.encode(json.dumps(event_data), encoding="UTF-8")
        f.write(encoded_string)
        f.seek(0)
        absolute_path = Path(f.name).absolute()
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(absolute_path)}):
            gh_mapper.initialize()

            assert os.environ.get("GITHUB_PR_URL", None) == str(
                event_data["pull_request"]["url"]
            )
            assert os.environ.get("GITHUB_PR_TITLE", None) == str(
                event_data["pull_request"]["title"]
            )
            assert os.environ.get("GITHUB_PR_ID", None) == str(
                event_data["pull_request"]["number"]
            )


def test_gh_pull_request_variable_set() -> None:
    # The test data is a subset of the full specification example:
    # https://docs.github.com/en/developers/webhooks-and-events/webhook-events-and-payloads#pull_request
    event_data: Dict[Any, Any] = {
        "action": "opened",
        "number": 2,
        "pull_request": {
            "url": "https://api.github.com/repos/Codertocat/Hello-World/pulls/2",
            "number": 2,
            "title": "Update the README with new information.",
        },
    }

    GitHubActionsMapper._set_pull_request_variables(event_data)

    assert os.environ.get("GITHUB_PR_URL", None) == str(
        event_data["pull_request"]["url"]
    )
    assert os.environ.get("GITHUB_PR_TITLE", None) == str(
        event_data["pull_request"]["title"]
    )
    assert os.environ.get("GITHUB_PR_ID", None) == str(
        event_data["pull_request"]["number"]
    )
