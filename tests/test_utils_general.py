import os
import re
from contextlib import nullcontext as does_not_raise
from typing import Any, Dict, Optional
from unittest import mock
from uuid import uuid4

import pytest

from kolga.settings import settings
from kolga.utils.exceptions import ImproperlyConfigured
from kolga.utils.general import (
    DEPLOY_NAME_MAX_HELM_NAME_LENGTH,
    camel_case_split,
    create_artifact_file_from_dict,
    deep_get,
    get_deploy_name,
    get_environment_vars_by_prefix,
    get_project_secret_var,
    get_secret_name,
    get_track,
    loads_json,
    string_to_yaml,
    truncate_with_hash,
    unescape_string,
)

DEFAULT_TRACK = os.environ.get("DEFAULT_TRACK", "stable")


@pytest.mark.parametrize(
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


@pytest.mark.parametrize(
    "slug, track, postfix, expected",
    [
        ("testing", DEFAULT_TRACK, None, "testing"),  # DEFAULT_TRACK is a special case
        ("testing", "qa", None, "testing-qa"),
        ("testing", "lizard", None, "testing-lizard"),
        ("testing", "1", None, "testing-1"),
        (
            "massively-long-environment-name",
            "staging",
            None,
            "massively-long-environment-nam-staging",
        ),
        (
            "massively-long-environment-name",
            "staging",
            "project-name",
            "massively-long-environment-nam-staging-project-name",
        ),
        (
            "massively-long-environment-name",
            "staging",
            "project-name-that-just-goes-on-and-on",
            "/massively-long-environment-nam-staging-project-nam-../",
        ),
    ],
)
def test_get_deploy_name(
    slug: str,
    track: str,
    postfix: Optional[str],
    expected: str,
) -> None:
    with mock.patch.object(settings, "ENVIRONMENT_SLUG", slug):
        deploy_name = get_deploy_name(track=track, postfix=postfix)

    assert len(deploy_name) <= DEPLOY_NAME_MAX_HELM_NAME_LENGTH

    if expected.startswith("/") and expected.endswith("/"):
        # Treat as a regular expression
        assert re.match(f"^{expected[1:-1]}$", deploy_name)
    else:
        assert deploy_name == expected


@pytest.mark.parametrize(
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


def test_get_environment_vars_by_prefix() -> None:
    prefix = f"TEST_{str(uuid4())}_SECRET_"

    env_vars = {f"{prefix}PASSWORD": "pass", f"{prefix}LIZARD": "-1"}
    secrets = {"PASSWORD": "pass", "LIZARD": "-1"}

    for key, secret in env_vars.items():
        os.environ[key] = secret

    assert get_environment_vars_by_prefix(prefix) == secrets


@pytest.mark.parametrize(
    "dictionary, keys, expected_value",
    [
        ({"test": True}, "test", True),
        ({"test", True}, "test.novalue", None),
        ({"test": True}, "novalue.level_one", None),
        ({"test": True}, "", None),
        ({"test": {"level_one": True}}, "test.level_one", True),
        ({"test": {"level_one": True}}, "test.level_two", None),
        ({"test": {"level_one": True}}, "test", {"level_one": True}),
    ],
)
def test_deep_get(
    dictionary: Dict[Any, Any], keys: str, expected_value: Optional[bool]
) -> None:
    assert deep_get(dictionary, keys) == expected_value


@pytest.mark.parametrize(
    "value, expected_value",
    (
        ("Hello World!", None),  # No escape, no change
        ("Héllö Wõrlð!", None),  # No escape, no change
        ("Hello\nworld!", None),  # Newlines should be preserved
        ("こんにちは世界", None),  # Wide chars should be preserved
        (r"Hello\nworld!", "Hello\nworld!"),  # Escaped newline should be un-escaped
        (r"Hello\tworld!", "Hello\tworld!"),  # Escaped tab should be un-escaped
        (r"Hello\\tworld!", r"Hello\tworld!"),  # Escaped backslash should be un-escaped
    ),
)
def test_unescape_string(value: str, expected_value: Optional[str]) -> None:
    if expected_value is None:
        expected_value = value

    unescaped_value = unescape_string(value)
    assert unescaped_value == expected_value


@pytest.mark.parametrize(
    "value, expected_value, indentation, strip",
    (
        ("Hello World", b"Hello World", 0, True),  # No change
        ("  Hello World!  ", b"Hello World!", 0, True),  # Strip
        ("  Hello World!  ", b"  Hello World!  ", 0, False),  # No strip
        ("Hello \n World", b"|-\nHello\nWorld", 0, True),  # \n in string + strip
        ("Hello \n World", b"|-\nHello \n World", 0, False),  # \n in string + no strip
        (" Hello World", b"  Hello World", 1, False),  # Indentation + no strip
        ("Hello World", b" Hello World", 1, True),  # Indentation + strip
        ("Hello World", b"    Hello World", 4, True),  # Indentation + strip
        (
            "Hello \n World",
            b"|-\n Hello\n World",
            1,
            True,
        ),  # Indentation + \n in string + strip
        (
            "Hello \n World",
            b"|-\n Hello \n  World",
            1,
            False,
        ),  # Indentation + \n in string + no strip
        (
            "Hello \n World",
            b"|-\n    Hello\n    World",
            4,
            True,
        ),  # Indentation + \n in string
    ),
)
def test_string_to_yaml(
    value: str, expected_value: bytes, indentation: int, strip: bool
) -> None:
    yaml_string = string_to_yaml(value, indentation=indentation, strip=strip)
    assert yaml_string == expected_value


def test_truncate_with_hash() -> None:
    truncated_string = truncate_with_hash("abcde", 4)
    assert truncated_string == "a-36"


def test_truncate_with_hash_exception() -> None:
    with pytest.raises(ValueError):
        truncate_with_hash("abd", 2)


@pytest.mark.parametrize(
    "project_name, variable_name, expected_value",
    (
        ("kolga", "key", "KOLGA_K8S_SECRET_KEY"),
        ("kolga", "key.-_!", "KOLGA_K8S_SECRET_KEY____"),
        ("kolga", "keyö", "KOLGA_K8S_SECRET_KEY_"),
    ),
)
def test_get_project_secret_var(
    project_name: str, variable_name: str, expected_value: str
) -> None:
    assert get_project_secret_var(project_name, variable_name) == expected_value


def test_create_artifact_file_from_dict(tmp_path: Any) -> None:
    filename = "test.env"
    data = {
        "TEST_VALUE1": "VAL1",
        "TEST_VALUE2": "VAL2",
    }
    assert_data = ["TEST_VALUE1=VAL1\n", "TEST_VALUE2=VAL2\n"]
    create_artifact_file_from_dict(env_dir=tmp_path, data=data, filename=filename)
    with open(tmp_path / filename) as file:
        file_lines = file.readlines()

    assert file_lines == assert_data


@pytest.mark.parametrize(
    "value, expected_value",
    (
        ("a", {}),
        ('{"test": "success"}', {"test": "success"}),
    ),
)
def test_loads_json(value: str, expected_value: Dict[str, Any]) -> None:
    assert loads_json(value) == expected_value


def test_loads_json_array_exception() -> None:
    with pytest.raises(TypeError):
        loads_json('["a", "b"]')


@pytest.mark.parametrize(
    "track, track_env, default_track, expected_value, assumption",
    (
        ("review", "staging", "stable", "review", does_not_raise()),
        ("", "staging", "stable", "staging", does_not_raise()),
        (None, "staging", "stable", "staging", does_not_raise()),
        (None, "", "stable", "stable", does_not_raise()),
        (None, "", "", None, pytest.raises(ImproperlyConfigured)),
    ),
)
def test_get_track(
    track: str,
    track_env: str,
    default_track: str,
    expected_value: str,
    assumption: Any,
) -> None:
    with mock.patch.object(settings, "DEFAULT_TRACK", default_track):
        with mock.patch.object(settings, "TRACK", track_env):
            with assumption:
                assert get_track(track) == expected_value
