import os
import re
from typing import Optional
from unittest import mock
from uuid import uuid4

import pytest

from kolga.settings import settings
from kolga.utils.general import (
    DEPLOY_NAME_MAX_HELM_NAME_LENGTH,
    camel_case_split,
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


def test_get_environment_vars_by_prefix() -> None:
    prefix = f"TEST_{str(uuid4())}_SECRET_"

    env_vars = {f"{prefix}PASSWORD": "pass", f"{prefix}LIZARD": "-1"}
    secrets = {"PASSWORD": "pass", "LIZARD": "-1"}

    for key, secret in env_vars.items():
        os.environ[key] = secret

    assert get_environment_vars_by_prefix(prefix) == secrets
