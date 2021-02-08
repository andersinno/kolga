from typing import Any
from unittest import mock

import pytest
import sentry_sdk
from sentry_sdk import capture_message
from sentry_sdk.utils import BadDsn

from tests.testcase import load_plugin

from ...exception import TestCouldNotLoadPlugin
from ..sentry import KolgaSentryPlugin


@mock.patch.dict(
    "os.environ",
    {
        "SENTRY_DSN": "https://test_dsn@example.com/1",
    },
)
@load_plugin(KolgaSentryPlugin)
def test_load_dsn() -> None:
    assert True


def test_load_without_env_vars_fail() -> None:
    with pytest.raises(TestCouldNotLoadPlugin):
        load_plugin(KolgaSentryPlugin).enable()


@mock.patch.dict(
    "os.environ",
    {
        "SENTRY_DSN": "test_dsn",
    },
)
def test_load_dsn_fail() -> None:
    with pytest.raises(BadDsn):
        load_plugin(KolgaSentryPlugin).enable()


@mock.patch.dict(
    "os.environ",
    {
        "SENTRY_DSN": "https://test_dsn@example.com/1",
    },
)
@load_plugin(KolgaSentryPlugin)
@mock.patch.object(sentry_sdk.Hub, "capture_event", return_value=True)
def test_send_message(capture_event: Any) -> None:
    capture_message("Something went wrong")
    capture_event.assert_called_once()
