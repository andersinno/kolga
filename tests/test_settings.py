import json
import tempfile
from pathlib import Path
from random import sample
from string import ascii_lowercase
from typing import Any, Dict, Optional, Set, Type
from unittest import mock

import pytest

import kolga
from kolga.hooks.plugins import PluginBase
from kolga.settings import GitHubActionsMapper, Settings, settings
from tests import MockEnv


def fake_track(invalid_value: str) -> str:
    if invalid_value:
        n_chars = len(invalid_value)
        unsuitables = {invalid_value}
    else:
        n_chars = 8
        unsuitables = set()

    return generate_random_string(n_chars, unsuitables)


def generate_random_string(n_chars: int, unsuitables: Optional[Set[str]] = None) -> str:
    if unsuitables is None:
        unsuitables = set()

    while True:
        ret = "".join(sample(ascii_lowercase, n_chars))
        if ret not in unsuitables:
            return ret


def kubeconfig_key(track: Optional[str] = None) -> str:
    track_postfix = f"_{track.upper()}" if track is not None else ""
    return f"KUBECONFIG{track_postfix}"


@pytest.mark.parametrize(
    "variables_to_set, expected_key",
    [
        (
            # Env takes precedence over everything else
            ["GIT_COMMIT_SHA", "TESTING_GIT_COMMIT_SHA", "CI_COMMIT_SHA"],
            "GIT_COMMIT_SHA",
        ),
        (
            # Project prefixed env var
            ["-GIT_COMMIT_SHA", "TESTING_GIT_COMMIT_SHA", "CI_COMMIT_SHA"],
            "TESTING_GIT_COMMIT_SHA",
        ),
        (
            # CI mapper is used if value is not in env
            ["-GIT_COMMIT_SHA", "CI_COMMIT_SHA"],
            "CI_COMMIT_SHA",
        ),
        (
            # Default value is used if all else fails
            ["-GIT_COMMIT_SHA"],
            None,
        ),
    ],
)
def test_set_variables(
    mockenv: MockEnv,
    variables_to_set: Dict[str, str],
    expected_key: Optional[str],
    attr_name: str = "GIT_COMMIT_SHA",
    value_length: int = 12,
) -> None:
    default_value = generate_random_string(value_length)
    used_values = {default_value}

    extra_env: Dict[str, Optional[str]] = {"GITLAB_CI": "1"}
    for key in variables_to_set:
        if key[0] == "-":
            # Remove key from environment
            extra_env[key[1:]] = None
        else:
            # Set a random value for an environment variable
            value = generate_random_string(value_length, used_values)
            extra_env[key] = value
            used_values.add(value)

    # Patch environment
    with mockenv(extra_env) as env:
        # Patch variable definitions
        parser, _ = kolga.settings._VARIABLE_DEFINITIONS[attr_name]
        with mock.patch.dict(
            "kolga.settings._VARIABLE_DEFINITIONS", {attr_name: [parser, default_value]}
        ):
            settings = Settings()

        # Get values
        if expected_key is None:
            expected_value = default_value
        else:
            expected_value = env[expected_key]
        value = getattr(settings, attr_name)

    assert (
        value == expected_value
    ), f"settings.{attr_name} != os.environ[{expected_key}]."


@pytest.mark.parametrize(
    "track, is_track_present, expected_variable",
    [
        ("", True, "KUBECONFIG"),
        ("stable", True, "KUBECONFIG_STABLE"),
        ("review", False, "KUBECONFIG"),
    ],
)
def test_setup_kubeconfig_with_track(
    mockenv: MockEnv, track: str, is_track_present: bool, expected_variable: str
) -> None:
    extra_env = {
        kubeconfig_key(): "Value from fall-back KUBECONFIG",
        kubeconfig_key(fake_track(track)): "A totally wrong KUBECONFIG",
    }

    if is_track_present:
        extra_env[kubeconfig_key(track)] = "Value from track-specific KUBECONFIG"

    with mockenv(extra_env) as env:
        expected_value = env[expected_variable]
        value, variable = settings.setup_kubeconfig(track)
        kubeconfig = env["KUBECONFIG"]

    assert (value, variable) == (expected_value, expected_variable)
    assert settings.KUBECONFIG == kubeconfig == expected_value


def test_setup_kubeconfig_raw(mockenv: MockEnv) -> None:
    extra_env = {"KUBECONFIG_RAW": "This value is from KUBECONFIG_RAW"}

    with mockenv(extra_env):
        filename, key = settings.setup_kubeconfig("fake_track")

    with open(filename) as fobj:
        result = fobj.read()

    assert key == "KUBECONFIG_RAW"
    assert "This value is from KUBECONFIG_RAW" == result


# KUBECONFIG_RAW is available but empty. Setup should fall back to KUBECONFIG
def test_setup_kubeconfig_raw_empty(mockenv: MockEnv) -> None:
    extra_env = {"KUBECONFIG_RAW": "", "KUBECONFIG": "Value from KUBECONFIG"}

    with mockenv(extra_env):
        value, key = settings.setup_kubeconfig("fake_track")

    assert key == "KUBECONFIG"
    assert value == "Value from KUBECONFIG"


def test_setup_kubeconfig_raw_with_track(mockenv: MockEnv) -> None:
    extra_env = {
        "KUBECONFIG_RAW": "This value is from KUBECONFIG_RAW",
        "KUBECONFIG_RAW_STABLE": "This value is from KUBECONFIG_RAW_STABLE",
    }

    with mockenv(extra_env):
        value, key = settings.setup_kubeconfig("STABLE")

    assert key == "KUBECONFIG_RAW_STABLE"


@mock.patch.dict("os.environ", {"TEST_PLUGIN_VARIABLE": "odins_raven"})
def test_load_unload_plugins(test_plugin: Type[PluginBase]) -> None:
    assert settings._load_plugin(plugin=test_plugin)[0] is True
    assert settings._unload_plugin(plugin=test_plugin)


def test_gh_event_data_set(mockenv: MockEnv) -> None:
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

    gh_mapper = GitHubActionsMapper()

    with tempfile.NamedTemporaryFile(mode="w") as f:
        json.dump(event_data, f)
        f.seek(0)

        env = {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_EVENT_PATH": str(Path(f.name).absolute()),
        }
        with mockenv(env):
            gh_mapper.initialize()

    assert gh_mapper.PR_URL == str(event_data["pull_request"]["url"])
    assert gh_mapper.PR_TITLE == str(event_data["pull_request"]["title"])
    assert gh_mapper.PR_ID == str(event_data["pull_request"]["number"])


def test_string_unescaping(mockenv: MockEnv) -> None:
    env = {
        "GITHUB_ACTIONS": "1",
        "K8S_ADDITIONAL_HOSTNAMES": r"foo\tbar,fizz\\buzz",
        "PROJECT_DIR": r"Hello\nworld!",
    }
    with mockenv(env):
        s = Settings()
        assert s.K8S_ADDITIONAL_HOSTNAMES == ["foo\tbar", "fizz\\buzz"]
        assert s.PROJECT_DIR == "Hello\nworld!"
        assert s.BUILDKIT_CACHE_REPO == ""  # Not set. Should be an empty string.
