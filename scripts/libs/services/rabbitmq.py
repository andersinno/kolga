from typing import Any, Dict, Mapping

from scripts.libs.database import Database
from scripts.libs.service import Service
from scripts.settings import settings
from scripts.utils.general import (
    AMQP,
    DATABASE_DEFAULT_PORT_MAPPING,
    RABBITMQ,
    get_deploy_name,
)
from scripts.utils.url import URL  # type: ignore


class RabbitmqService(Service):
    def __init__(
        self,
        chart: str = "stable/rabbitmq",
        chart_version: str = "6.16.6",
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
        self.values = {
            "image": {"tag": self.rabbitmq_version},
            "rabbitmq": {"password": self.password, "username": self.username},
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

    def get_artifacts(self) -> Mapping[str, str]:
        server_url = self.get_base_server_url()

        return {
            self.get_service_secret_artifact_name(service=service): str(server_url)
            for service in self._prerequisite_of
        }
