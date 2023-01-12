from typing import Any, Dict, Mapping, TypedDict

from kolga.libs.service import Service
from kolga.settings import settings
from kolga.utils.general import (
    DATABASE_DEFAULT_PORT_MAPPING,
    POSTGRES,
    get_deploy_name,
    get_project_secret_var,
)
from kolga.utils.models import DockerImageRef, HelmValues
from kolga.utils.url import URL  # type: ignore


class _Image(TypedDict, total=False):
    registry: str
    repository: str
    tag: str


class _RequestLimits(TypedDict, total=False):
    memory: str
    cpu: str


class _Limits(TypedDict, total=False):
    requests: _RequestLimits


class _Values(HelmValues):
    fullnameOverride: str
    image: _Image
    postgresqlUsername: str
    postgresqlPassword: str
    postgresqlDatabase: str
    resources: _Limits


class PostgresqlService(Service):
    """
    TODO: Add support for multiple databases within one server
    """

    def __init__(
        self,
        chart: str = "bitnami/postgresql",
        chart_version: str = "10.16.0",
        username: str = settings.DATABASE_USER,
        password: str = settings.DATABASE_PASSWORD,
        database: str = settings.DATABASE_DB,
        artifact_name: str = "DATABASE_URL",
        **kwargs: Any,
    ) -> None:
        kwargs["name"] = POSTGRES
        kwargs["chart"] = chart
        kwargs["chart_version"] = chart_version
        kwargs["artifact_name"] = artifact_name
        super().__init__(**kwargs)

        self.username = username
        self.password = password
        self.database = database
        image = DockerImageRef.parse_string(settings.POSTGRES_IMAGE)

        self.memory_request = self.service_specific_values.get("MEMORY_REQUEST", "50Mi")
        self.cpu_request = self.service_specific_values.get("CPU_REQUEST", "50m")

        self.values: _Values = {
            "image": {"repository": image.repository},
            "fullnameOverride": get_deploy_name(track=self.track, postfix=self.name),
            "postgresqlUsername": self.username,
            "postgresqlPassword": self.password,
            "postgresqlDatabase": self.database,
            "resources": {
                "requests": {"memory": self.memory_request, "cpu": self.cpu_request},
            },
        }

        if image.registry is not None:
            self.values["image"]["registry"] = image.registry

        if image.tag is not None:
            self.values["image"]["tag"] = image.tag

    def get_database_url(self) -> URL:
        deploy_name = get_deploy_name(self.track)
        port = DATABASE_DEFAULT_PORT_MAPPING[POSTGRES]
        host = f"{deploy_name}-{POSTGRES}"

        return URL(
            drivername=POSTGRES,
            host=host,
            port=port,
            username=self.username,
            password=self.password,
            database=self.database,
        )

    def _get_default_database_values(
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
            get_project_secret_var(
                project_name=service_name, value="DATABASE_URL"
            ): str(url),
            get_project_secret_var(
                project_name=service_name, value="DATABASE_HOST"
            ): str(url.host),
            get_project_secret_var(project_name=service_name, value="DATABASE_DB"): str(
                url.database
            ),
            get_project_secret_var(
                project_name=service_name, value="DATABASE_PORT"
            ): str(url.port),
            get_project_secret_var(
                project_name=service_name, value="DATABASE_USERNAME"
            ): str(url.username),
            get_project_secret_var(
                project_name=service_name, value="DATABASE_PASSWORD"
            ): str(url.password),
        }

    def get_artifacts(self) -> Mapping[str, str]:
        artifacts = {}
        for service in self._prerequisite_of:
            main_artifact_name = self.get_service_secret_artifact_name(service=service)
            artifacts[main_artifact_name] = str(self.get_database_url())
            artifacts.update(
                self._get_default_database_values(
                    url=self.get_database_url(), service_name=service.name
                )
            )
        return artifacts
