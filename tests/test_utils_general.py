import os
import re
from typing import Any, Dict, Optional
from unittest import mock
from uuid import uuid4

import pytest

from kolga.settings import settings
from kolga.utils.general import (
    DEPLOY_NAME_MAX_HELM_NAME_LENGTH,
    camel_case_split,
    deep_get,
    get_deploy_name,
    get_environment_vars_by_prefix,
    get_secret_name,
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
