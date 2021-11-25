from typing import Any, List, Optional, cast
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
    results: Any = settings.plugin_manager.hook.project_deployment_complete(
        exception=None,
        namespace="review",
        project=Project(track="review", url="test.example.com"),
        track="review",
    )
    results = cast(List[Optional[bool]], results)
    assert len(results) == 1 and results[0] is True
    mock_post_message.assert_called_once()
