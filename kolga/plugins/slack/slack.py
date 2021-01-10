from typing import TYPE_CHECKING, Optional

from environs import Env
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from kolga.hooks import hookimpl
from kolga.hooks.plugins import PluginBase
from kolga.utils.logger import logger

from .messages import new_environment_message

if TYPE_CHECKING:
    from kolga.libs.project import Project


class KolgaSlackPlugin(PluginBase):

    name = "slack"
    verbose_name = "Kolga Slack Plugin"
    version = 0.1

    # Environment variables
    SLACK_TOKEN: str
    SLACK_CHANNEL: str

    def __init__(self, env: Env) -> None:
        self.required_variables = [("SLACK_TOKEN", env.str), ("SLACK_CHANNEL", env.str)]
        self.configure(env)
        self.client = WebClient(self.SLACK_TOKEN)

    @hookimpl
    def project_deployment_complete(
        self, project: "Project", track: str, namespace: str
    ) -> Optional[bool]:
        if not self.configured:
            return None

        deployment_message = new_environment_message(track, project)

        try:
            self.client.chat_postMessage(
                channel=self.SLACK_CHANNEL,
                blocks=deployment_message,
                username="Kolga Deployment",
                icon_emoji=":rocket:",
            )
        except SlackApiError as e:
            logger.error(
                message=f"Could not send slack message -> {e.response['error']}"
            )

        return True
