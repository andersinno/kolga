from typing import Any, Dict, Mapping, TypedDict

from kolga.libs.database import Database
from kolga.libs.service import Service
from kolga.settings import settings
from kolga.utils.general import (
    AMQP,
    DATABASE_DEFAULT_PORT_MAPPING,
    RABBITMQ,
    get_deploy_name,
    get_project_secret_var,
)
from kolga.utils.models import HelmValues
from kolga.utils.url import URL  # type: ignore


class _Image(TypedDict):
    tag: str


class _RabbitMQ(TypedDict):
    password: str
    username: str


class _Values(HelmValues):
    image: _Image
    auth: _RabbitMQ


class RabbitmqService(Service):
    def __init__(
        self,
        chart: str = "bitnami/rabbitmq",
        chart_version: str = "8.26.3",
        username: str = settings.DATABASE_USER,
        password: str = settings.DATABASE_PASSWORD,
        vhost: str = "default",
        artifact_name: str = "CELERY_BROKER_URI",
        rabbitmq_version: str = settings.RABBITMQ_VERSION_TAG,
        **kwargs: Any,
    ) -> None:
        kwargs["name"] = RABBITMQ
        kwargs["chart"] = chart
        kwargs["chart_version"] = chart_version
        kwargs["artifact_name"] = artifact_name

        super().__init__(**kwargs)
        self.username = username
        self.password = password
        self.vhost = vhost
        self.rabbitmq_version = rabbitmq_version
        self.__databases: Dict[str, Database] = {}
        self.values: _Values = {
            "image": {"tag": self.rabbitmq_version},
            "auth": {"password": self.password, "username": self.username},
        }

    def get_base_server_url(self) -> URL:
        deploy_name = get_deploy_name(self.track)
        port = DATABASE_DEFAULT_PORT_MAPPING[AMQP]
        host = f"{deploy_name}-rabbitmq"
        return URL(
            drivername=AMQP,
            host=host,
            port=port,
            username=self.username,
            password=self.password,
        )

    def _get_default_broker_values(
        self, url: URL, service_name: str = ""
    ) -> Dict[str, str]:
        """
        Return a set of default extra values that are non-user definable

        Currently there is only support for the user to set a single value when
        adding a service. This adds some default values in order for the application
        to be able to get every part of the database URL separately.

        Args:
            url: The URL of the database as a single string
            service_name: Prefixes for each value

        Returns:

        """
        return {
            get_project_secret_var(project_name=service_name, value="BROKER_URL"): str(
                url
            ),
            get_project_secret_var(project_name=service_name, value="BROKER_HOST"): str(
                url.host
            ),
            get_project_secret_var(project_name=service_name, value="BROKER_PORT"): str(
                url.port
            ),
            get_project_secret_var(
                project_name=service_name, value="BROKER_USERNAME"
            ): str(url.username),
            get_project_secret_var(
                project_name=service_name, value="BROKER_PASSWORD"
            ): str(url.password),
        }

    def get_artifacts(self) -> Mapping[str, str]:
        artifacts = {}
        for service in self._prerequisite_of:
            main_artifact_name = self.get_service_secret_artifact_name(service=service)
            artifacts[main_artifact_name] = str(self.get_base_server_url())
            artifacts.update(
                self._get_default_broker_values(
                    url=self.get_base_server_url(), service_name=service.name
                )
            )
        return artifacts
