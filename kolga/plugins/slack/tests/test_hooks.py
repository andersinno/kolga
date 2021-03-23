from typing import Any
from unittest import mock

import slack_sdk

from kolga.libs.project import Project
from kolga.settings import settings
from tests.testcase import load_plugin

from ..slack import KolgaSlackPlugin


@mock.patch.dict(
    "os.environ",
    {
        "SLACK_TOKEN": "test_token",
        "SLACK_CHANNEL": "kolga-test",
    },
)
@load_plugin(KolgaSlackPlugin)
@mock.patch.object(
    slack_sdk.web.client.WebClient, "chat_postMessage", return_value=True
)
def test_project_deployment_complete(mock_post_message: Any) -> None:
    results = settings.plugin_manager.hook.project_deployment_complete(
        project=Project(track="review", url="test.example.com"),
        track="review",
        namespace="review",
    )
    assert len(results) == 1 and results[0] is True
    mock_post_message.assert_called_once()
