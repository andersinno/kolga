from unittest import mock

import pytest

from tests.testcase import load_plugin

from ...exceptions import TestCouldNotLoadPlugin
from ..binfmt import KolgaBinfmtPlugin


@mock.patch.dict(
    "os.environ",
    {
        "BINFMT_ENABLED": "1",
        "DOCKER_BUILD_PLATFORMS": "linux/amd64, linux/arm64",
    },
)
@load_plugin(KolgaBinfmtPlugin)
def test_load_plugin() -> None:
    pass


@mock.patch.dict(
    "os.environ",
    {
        "BINFMT_ENABLED": "1",
    },
)
def test_load_plugin_no_platforms() -> None:
    with pytest.raises(TestCouldNotLoadPlugin):
        load_plugin(KolgaBinfmtPlugin).enable()


@mock.patch.dict(
    "os.environ",
    {
        "BINFMT_ENABLED": "0",
    },
)
def test_load_plugin_no_platforms_disabled_plugin() -> None:
    with pytest.raises(TestCouldNotLoadPlugin):
        load_plugin(KolgaBinfmtPlugin).enable()
