import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping, TypedDict
from uuid import uuid4

from kolga.libs.database import Database
from kolga.libs.service import Service
from kolga.settings import settings
from kolga.utils.general import (
    DATABASE_DEFAULT_PORT_MAPPING,
    MYSQL,
    get_deploy_name,
    get_project_secret_var,
    string_to_yaml,
)
from kolga.utils.models import HelmValues
from kolga.utils.url import URL  # type: ignore


class _Auth(TypedDict):
    database: str
    password: str
    rootPassword: str
    username: str


class _Image(TypedDict):
    tag: str


class _Values(HelmValues):
    auth: _Auth
    image: _Image


class MysqlService(Service):
    def __init__(
        self,
        chart: str = "bitnami/mysql",
        chart_version: str = "8.8.22",
        username: str = settings.DATABASE_USER,
        password: str = settings.DATABASE_PASSWORD,
        database: str = settings.DATABASE_DB,
        artifact_name: str = "DATABASE_URL",
        mysql_version: str = settings.MYSQL_VERSION_TAG,
        **kwargs: Any,
    ) -> None:
        kwargs["name"] = MYSQL
        kwargs["chart"] = chart
        kwargs["chart_version"] = chart_version
        kwargs["artifact_name"] = artifact_name

        super().__init__(**kwargs)
        self.username = username
        self.password = password
        self.database = database
        self.mysql_version = mysql_version
        self.__databases: Dict[Service, Database] = {}
        self.values: _Values = {
            "auth": {
                "database": self.database,
                "password": self.password,
                "rootPassword": self.password,
                "username": self.username,
            },
            "image": {"tag": self.mysql_version},
        }

    def setup_prerequisites(self) -> None:
        if self._prerequisite_of:
            self.__databases = self._setup_database_init()

    def get_base_database_url(self) -> URL:
        deploy_name = get_deploy_name(self.track)
        port = DATABASE_DEFAULT_PORT_MAPPING[MYSQL]
        host = f"{deploy_name}-{MYSQL}"

        return URL(drivername=MYSQL, host=host, port=port)

    def _setup_database_init(self) -> Dict[Service, Database]:
        databases = {}
        database_values_file = tempfile.NamedTemporaryFile(delete=False)
        values_file = Path(database_values_file.name)
        database_values_file.write(b"initializationFiles: \n")
        for dependent in self._prerequisite_of:
            database_url = self.get_base_database_url()
            database_url.username = str(uuid4()).replace("-", "")
            database_url.password = str(uuid4()).replace("-", "")
            database_url.database = dependent.name
            database = Database(url=database_url)

            database_values_file.write(
                string_to_yaml(f"{dependent.name}.sql: ", indentation=2, strip=False)
            )

            yaml_sql_string = string_to_yaml(database.creation_sql, indentation=4)
            database_values_file.write(yaml_sql_string)
            database_values_file.write(b"\n")
            databases[dependent] = database
        database_values_file.close()
        self.values_files.append(values_file)
        return databases

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
        for service, database in self.__databases.items():
            main_artifact_name = self.get_service_secret_artifact_name(service=service)
            artifacts[main_artifact_name] = str(database.url)
            artifacts.update(
                self._get_default_database_values(
                    url=database.url, service_name=service.name
                )
            )
        return artifacts
