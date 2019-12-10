import shutil
from base64 import b64encode
from pathlib import Path
from typing import Any, Dict, Optional

import colorful as cf
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from scripts.utils.logger import logger
from scripts.utils.models import SubprocessResult

from ..libs.helm import Helm
from ..settings import settings
from ..utils.exceptions import NoClusterConfigError
from ..utils.general import (
    MYSQL,
    POSTGRES,
    camel_case_split,
    get_database_type,
    get_database_url,
    get_deploy_name,
    get_environment_vars_by_prefix,
    get_secret_name,
    loads_json,
    run_os_command,
)


class Kubernetes:
    """
    A wrapper class around various Kubernetes tools and functions

    The class works as a one-stop-shop for handling resources in
    Kubernetes. It does so by utilizing not only `kubectl` but also
    Kubernets own API through the `kubernetes` Python package
    and Helm through the Python `helm` package.
    """

    ICON = "☸️"

    def __init__(self, track: str = settings.DEFAULT_TRACK) -> None:
        self.client = self.create_client(track=track)
        self.helm = Helm()

    def create_client(self, track: str) -> k8s_client.ApiClient:
        try:
            kubeconfig, method = settings.setup_kubeconfig(track)
        except NoClusterConfigError as exc:
            logger.error(
                icon=f"{self.ICON}  🔑",
                message="Can't log in to Kubernetes cluster, all auth methods exhausted",
                error=exc,
                raise_exception=True,
            )

        logger.success(
            icon=f"{self.ICON}  🔑", message=f"Using {method} for Kubernetes auth",
        )

        config = k8s_client.Configuration()
        k8s_config.load_kube_config(
            client_configuration=config, config_file=kubeconfig,
        )

        return k8s_client.ApiClient(configuration=config)

    @staticmethod
    def _is_client_error(status: Any) -> bool:
        """
        Checks if a value is a client HTTP error

        Args:
            status: None or a integer castable value

        Returns:
            True of the value is a client error, else False
        """
        return status is not None and 400 <= int(status) < 500

    @staticmethod
    def labels_to_string(labels: Dict[str, str]) -> str:
        """
        Creates a string representation of a dict that can
        be used when passing values to Kubernetes.

        Args:
            labels: Testing

        Returns:
            A comma separated string of style ``key=value,key2=value2``
        """
        return ",".join([f"{key}={value}" for (key, value) in labels.items()])

    @staticmethod
    def _handle_api_error(
        error: ApiException, raise_client_exception: bool = False
    ) -> Any:
        """
        Handle a ApiException from the Kubernetes client

        Args:
            error: ApiException to handle
            raise_client_exception: Should the method raise an error on client errors

        Returns:
            The the stringified version of the errors JSON body

        Raises:
            ApiException: If the ``raise_client_exception`` argument is set to ``True``
        """
        error_body = loads_json(error.body)
        if not error_body:
            error_body = {"message": "An unknown error occurred"}
        if Kubernetes._is_client_error(error.status):
            reason = camel_case_split(str(error_body.get("reason", "Unknown")))
            print(
                f"{cf.yellow}{cf.bold}{reason}{cf.reset}"
                f" ({error.status} {cf.italic}{error_body['message'].capitalize()}{cf.reset})"
            )
            if raise_client_exception:
                raise error
        else:
            logger.error(error=error, raise_exception=True)
        return error_body

    @staticmethod
    def _encode_secret(data: Dict[str, str]) -> Dict[str, str]:
        """
        Base64 values of a dict

        Kubernetes requires base64 encoded values to be sent instead
        of plain text when creating secrets or config maps. This method
        takes care of base64 encoding values of a dict using UTF-8 encoding.

        Args:
            data: dict to be encoded

        Returns:
            Dict with base64 encoded values
        """
        encoded_dict = {}
        for k, v in data.items():
            encoded_dict[k] = b64encode(v.encode("UTF-8")).decode("UTF-8")
        return encoded_dict

    @staticmethod
    def get_environments_secrets_by_prefix(
        prefix: str = settings.K8S_SECRET_PREFIX,
    ) -> Dict[str, Any]:
        """
        Extract all environment variables with a prefix

        Environment variables strting with the `prefix` attribute are
        extracted and put into a dict.

        Args:
            prefix: Prefix to environment key that should be extracted

        Returns:
            A dict of keys stripped of the prefix and the value as given
            in the environment variable.
        """
        return get_environment_vars_by_prefix(prefix)

    def create_namespace(self, namespace: str = settings.K8S_NAMESPACE) -> str:
        """
        Create a Kubernetes namespace

        Args:
            namespace: Name of the namespace to create

        Returns:
            On success, returns the name of the namespace

        Raises:
            ApiException: If the namespace creation fails by other means than a
                          namespace conflict, something that happens if the
                          namespace already exists.
        """
        v1 = k8s_client.CoreV1Api(self.client)
        v1_metadata = k8s_client.V1ObjectMeta(name=namespace, labels={"app": "kubed"})
        v1_namespace = k8s_client.V1Namespace(metadata=v1_metadata)
        logger.info(
            icon=f"{self.ICON}  🔨", title=f"Creating namespace {namespace}: ", end=""
        )

        try:
            v1.create_namespace(v1_namespace)
        except ApiException as e:
            self._handle_api_error(e)
            if e.status != 409:  # Namespace exists
                raise e
        logger.success()
        return namespace

    def create_secret(self, data: Dict[str, str], namespace: str, track: str) -> str:
        deploy_name = get_deploy_name(track=track)
        secret_name = get_secret_name(track=track)
        v1 = k8s_client.CoreV1Api(self.client)
        v1_metadata = k8s_client.V1ObjectMeta(
            name=secret_name, namespace=namespace, labels={"release": deploy_name}
        )

        encoded_data = self._encode_secret(data)
        body = k8s_client.V1Secret(
            data=encoded_data, metadata=v1_metadata, type="generic"
        )
        logger.info(
            icon=f"{self.ICON}  🔨",
            title=f"Creating secret '{secret_name}' for namespace '{namespace}': ",
            end="",
        )
        try:
            v1.create_namespaced_secret(namespace=namespace, body=body)
        except ApiException:
            try:
                v1.replace_namespaced_secret(
                    name=secret_name, namespace=namespace, body=body
                )
            except ApiException as e:
                self._handle_api_error(e, raise_client_exception=True)
        logger.success()
        return secret_name

    def create_secrets_from_environment(self, namespace: str, track: str) -> str:
        secrets = self.get_environments_secrets_by_prefix()
        return self.create_secret(data=secrets, namespace=namespace, track=track)

    def setup_helm(self) -> None:
        self.helm.setup_helm()

    def create_database_deployment(
        self, namespace: str, track: str, database_type: Optional[str] = None,
    ) -> None:
        if not database_type:
            database_type = get_database_type()
        if not database_type:
            return None

        if database_type == POSTGRES:
            self.create_postgres_database(namespace=namespace, track=track)
        elif database_type == MYSQL:
            self.create_mysql_database(namespace=namespace, track=track)

    def create_postgres_database(self, namespace: str, track: str) -> None:
        helm_chart = "stable/postgresql"
        deploy_name = f"{get_deploy_name(track=track)}-db"
        values = {
            "image.tag": settings.POSTGRES_VERSION_TAG,
            "postgresqlUsername": settings.DATABASE_USER,
            "postgresqlPassword": settings.DATABASE_PASSWORD,
            "postgresqlDatabase": settings.DATABASE_DB,
        }
        self.helm.upgrade_chart(
            chart=helm_chart, name=deploy_name, namespace=namespace, values=values,
        )

    def create_mysql_database(self, namespace: str, track: str) -> None:
        helm_chart = "stable/mysql"
        deploy_name = f"{get_deploy_name(track=track)}-db"
        values = {
            "imageTag": settings.MYSQL_VERSION_TAG,
            "mysqlUser": settings.DATABASE_USER,
            "mysqlPassword": settings.DATABASE_PASSWORD,
            "mysqlRootPassword": settings.DATABASE_PASSWORD,
            "mysqlDatabase": settings.DATABASE_DB,
            "testFramework.enabled": "false",
        }
        self.helm.upgrade_chart(
            chart=helm_chart, name=deploy_name, namespace=namespace, values=values,
        )

    def create_application_deployment(
        self, docker_image: str, secret_name: str, namespace: str, track: str,
    ) -> None:
        deploy_name = get_deploy_name(track=track)
        application_path = Path(settings.PROJECT_DIR)
        helm_path = application_path / "helm"
        auto_helm_path = Path("/tmp/devops/ci-configuration/helm")
        if not helm_path.exists() and auto_helm_path.exists():
            shutil.copytree(auto_helm_path, helm_path)
        else:
            logger.error(
                message="Could not find Helm chart to use",
                error=OSError(),
                raise_exception=True,
            )

        database_url = get_database_url(track=track)
        values: Dict[str, str] = {
            "namespace": namespace,
            "image": docker_image,
            "gitlab.app": settings.PROJECT_PATH_SLUG,
            "gitlab.env": settings.ENVIRONMENT_SLUG,
            "releaseOverride": settings.ENVIRONMENT_SLUG,
            "application.track": track,
            "application.database_url": str(database_url),
            "application.database_host": str(database_url.host),
            "application.secretName": secret_name,
            "application.initializeCommand": settings.APP_INITIALIZE_COMMAND,
            "application.migrateCommand": settings.APP_MIGRATE_COMMAND,
            "service.url": settings.ENVIRONMENT_URL,
            "service.targetPort": settings.SERVICE_PORT,
        }

        self.helm.upgrade_chart(
            chart_path=helm_path, name=deploy_name, namespace=namespace, values=values,
        )

    def delete(
        self,
        resource: str,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        namespace: str = settings.K8S_NAMESPACE,
    ) -> None:
        os_command = [
            "kubectl",
            "delete",
            resource,
            "--include-uninitialized",
            "--ignore-not-found",
            f"--namespace={namespace}",
        ]

        logger.info(icon=f"{self.ICON}  🗑️ ", title=f"Removing {resource}", end="")
        if labels:
            labels_str = self.labels_to_string(labels)
            os_command += ["-l", labels_str]
            logger.info(title=f" with labels {labels_str}", end="")
        if name:
            os_command += [name]
            logger.info(title=f" with name '{name}'", end="")
        logger.info(": ", end="")
        result = run_os_command(os_command, shell=True)
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=True)

    def delete_all(
        self,
        labels: Optional[Dict[str, str]] = None,
        namespace: str = settings.K8S_NAMESPACE,
    ) -> None:
        resource = (
            "all,"
            "ingress,"
            "storageClasses,"
            "volumeattachments,"
            "persistentvolumeclaims,"
            "persistentvolumes,"
            "configmaps,"
            "rolebinding,"
            "role,"
            "secrets"
        )
        self.delete(resource=resource, labels=labels, namespace=namespace)

    def delete_namespace(self, namespace: str = settings.K8S_NAMESPACE) -> None:
        self.delete(resource="namespace", name=namespace)

    def get(
        self,
        resource: str,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        namespace: str = settings.K8S_NAMESPACE,
        raise_exception: bool = True,
    ) -> SubprocessResult:
        os_command = ["kubectl", "get", resource, f"--namespace={namespace}"]

        logger.info(icon=f"{self.ICON}  🗑️ ", title=f"Getting {resource}", end="")
        if labels:
            labels_str = self.labels_to_string(labels)
            os_command += ["-l", labels_str]
            logger.info(title=f" with labels {labels_str}", end="")
        if name:
            os_command += [name]
            logger.info(title=f" with name '{name}'", end="")
        logger.info(": ", end="")
        result = run_os_command(os_command, shell=True)
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=raise_exception)
        return result
