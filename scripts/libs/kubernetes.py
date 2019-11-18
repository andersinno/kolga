import os
import shutil
import time
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
from ..utils.general import (
    MYSQL,
    POSTGRES,
    camel_case_split,
    get_database_type,
    get_database_url,
    get_deploy_name,
    get_secret_name,
    loads_json,
    run_os_command,
)


class KubernetesConfig(k8s_client.Configuration):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self.host = settings.K8S_API_URL
        self.api_key = {"authorization": f"Bearer {settings.K8S_API_KEY}"}
        self.ssl_ca_cert = settings.K8S_API_CA_PEM_FILE

    @staticmethod
    def can_configure() -> bool:
        return all(
            [settings.K8S_API_URL, settings.K8S_API_KEY, settings.K8S_API_CA_PEM_FILE]
        )


DEFAULT_TRACK = "stable"


class Kubernetes:
    ICON = "☸️"
    HELM_ICON = "⎈"

    def __init__(self) -> None:
        self.client = self.create_client()
        self.helm = Helm()

    def create_client(self) -> k8s_client.ApiClient:
        if settings.KUBECONFIG:
            logger.success(
                icon=f"{self.ICON}  🔑",
                message=f"Using KUBECONFIG for Kubernetes auth ({settings.KUBECONFIG})",
            )
            k8s_config.load_kube_config()
            return k8s_client.ApiClient()
        elif KubernetesConfig.can_configure():
            logger.success(
                icon=f"{self.ICON}  🔑", message=f"Using env vars for Kubernetes auth"
            )
            _config = KubernetesConfig()
            return k8s_client.ApiClient(_config)

        logger.error(
            icon=f"{self.ICON}  🔑",
            message="Can't log in to Kubernetes cluster, all auth methods exhausted",
            error=Exception(),
            raise_exception=True,
        )

    @staticmethod
    def _is_client_error(status: Any) -> bool:
        return status is not None and 400 <= int(status) < 500

    @staticmethod
    def labels_to_string(labels: Dict[str, str]) -> str:
        return ",".join([f"{key}={value}" for (key, value) in labels.items()])

    @staticmethod
    def _handle_api_error(e: ApiException, raise_client_exception: bool = False) -> Any:
        error_body = loads_json(e.body)
        if not error_body:
            error_body = {"message": "An unknown error occurred"}
        if Kubernetes._is_client_error(e.status):
            reason = camel_case_split(str(error_body.get("reason", "Unknown")))
            print(
                f"{cf.yellow}{cf.bold}{reason}{cf.reset}"
                f" ({e.status} {cf.italic}{error_body['message'].capitalize()}{cf.reset})"
            )
            if raise_client_exception:
                raise e
        else:
            logger.error("Could not create namespace", error=e, raise_exception=True)
        return error_body

    @staticmethod
    def _encode_secret(data: Dict[str, str]) -> Dict[str, str]:
        encoded_dict = {}
        for k, v in data.items():
            encoded_dict[k] = b64encode(v.encode("UTF-8")).decode("UTF-8")
        return encoded_dict

    @staticmethod
    def get_environments_secrets_by_prefix(
        prefix: str = settings.K8S_SECRET_PREFIX,
    ) -> Dict[str, Any]:
        return {
            key.replace(prefix, ""): value
            for key, value in os.environ.items()
            if key.startswith(prefix)
        }

    def create_namespace(self, namespace: str = settings.K8S_NAMESPACE) -> str:
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

    def create_secret(
        self,
        data: Dict[str, str],
        namespace: str = settings.K8S_NAMESPACE,
        track: str = DEFAULT_TRACK,
    ) -> str:
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

    def create_secrets_from_environment(
        self, namespace: str = settings.K8S_NAMESPACE, track: str = DEFAULT_TRACK
    ) -> str:
        secrets = self.get_environments_secrets_by_prefix()
        return self.create_secret(data=secrets, namespace=namespace, track=track)

    def setup_helm(self) -> None:
        self.helm.setup_helm()

    def create_database_deployment(
        self, database_type: Optional[str] = None, track: str = DEFAULT_TRACK
    ) -> None:
        if not database_type:
            database_type = get_database_type()
        if not database_type:
            return None

        if database_type == POSTGRES:
            self.create_postgres_database(track=track)
        elif database_type == MYSQL:
            self.create_mysql_database(track=track)

    def create_postgres_database(self, track: str = DEFAULT_TRACK) -> None:
        helm_chart = "stable/postgresql"
        deploy_name = get_deploy_name(track=track)
        values = {
            "image.tag": settings.POSTGRES_VERSION_TAG,
            "postgresqlUsername": settings.DATABASE_USER,
            "postgresqlPassword": settings.DATABASE_PASSWORD,
            "postgresqlDatabase": settings.DATABASE_DB,
            "nameOverride": "postgres",
        }
        self.helm.upgrade_chart(chart=helm_chart, name=deploy_name, values=values)

    def create_mysql_database(self, track: str = DEFAULT_TRACK) -> None:
        helm_chart = "stable/mysql"
        deploy_name = get_deploy_name(track=track)
        values = {
            "imageTag": settings.MYSQL_VERSION_TAG,
            "mysqlUser": settings.DATABASE_USER,
            "mysqlPassword": settings.DATABASE_PASSWORD,
            "mysqlRootPassword": settings.DATABASE_PASSWORD,
            "mysqlDatabase": settings.DATABASE_DB,
            "testFramework.enabled": "false",
        }
        self.helm.upgrade_chart(chart=helm_chart, name=deploy_name, values=values)

    def create_application_deployment(
        self, docker_image: str, secret_name: str, track: str = DEFAULT_TRACK
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
            "namespace": settings.K8S_NAMESPACE,
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

        self.helm.upgrade_chart(chart_path=helm_path, name=deploy_name, values=values)

    def apply(
        self,
        verbose_name: str,
        manifest_path: Path,
        namespace: str = settings.K8S_NAMESPACE,
    ) -> None:
        """
        Wrapper for `kubectl`s `apply` command

        While this could have been implemented using the Python lib
        same as other functions, it is very cumbersome and would
        create a lot of maintainability issues.

        Example of how this could be solved in Python can be found here:
        https://stackoverflow.com/questions/36307950/kubernetes-api-call-equivalent-to-kubectl-apply
        """
        logger.info(
            icon=f"{self.ICON}  ➡️",
            title=f"Applying {verbose_name} deployment: ",
            end="",
        )

        os_command = [
            "kubectl",
            "apply",
            "--recursive",
            "-f",
            str(manifest_path),
            f"--namespace='{namespace}'",
        ]

        result = run_os_command(os_command, shell=True)
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=True)

    def replace(
        self,
        verbose_name: str,
        manifest_path: Path,
        force: bool = True,
        namespace: str = settings.K8S_NAMESPACE,
    ) -> None:
        """
        Wrapper for `kubectl`s `replace` command
        """
        logger.info(
            icon=f"{self.ICON}  ↔️ ",
            title=f"Replacing {verbose_name} deployment: ",
            end="",
        )

        os_command = [
            "kubectl",
            "replace",
            "--recursive",
            "-f",
            str(manifest_path),
            f"--namespace='{namespace}'",
        ]
        if force:
            os_command.append("--force")

        result = run_os_command(os_command, shell=True)
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=True)

    def wait_to_exist(
        self,
        resource: str,
        labels: Optional[Dict[str, str]] = None,
        name: Optional[str] = None,
        wait_for: int = 15,
        namespace: str = settings.K8S_NAMESPACE,
        log_status: bool = True,
    ) -> bool:
        have_waited_for = 0
        while have_waited_for <= wait_for:
            time.sleep(1)
            have_waited_for += 1
            result = self.get(
                resource=resource, labels=labels, namespace=namespace, name=name
            )
            if not result.return_code:
                return True
            if log_status:
                logger.info(message="?", end="")
        return False

    def wait(
        self,
        resource: str,
        condition: str,
        labels: Optional[Dict[str, str]] = None,
        timeout: int = 300,
        retries: int = 0,
        is_retry: bool = False,
        wait_to_exist: int = 0,
        namespace: str = settings.K8S_NAMESPACE,
    ) -> None:
        """
        Wrapper for `kubectl`s `wait` command
        """
        if not labels:
            labels = {}
        labels_str = self.labels_to_string(labels)
        if not is_retry:
            logger.info(
                icon=f"{self.ICON}  🕐",
                title=f"Waiting for {resource} with labels {labels_str}: ",
                end="",
            )
        else:
            logger.info(message=".", end="")

        if wait_to_exist:
            if not self.wait_to_exist(
                resource=resource,
                labels=labels,
                namespace=namespace,
                wait_for=wait_to_exist,
            ):
                error_message = "Could not find resource to wait for"
                logger.error(message=error_message, error=TimeoutError(error_message))

        os_command = [
            "kubectl",
            "wait",
            resource,
            f"--timeout={timeout}s",
            f"--for=condition={condition}",
            "-l",
            labels_str,
            f'--namespace="{namespace}"',
        ]

        result = run_os_command(os_command, shell=True)
        if not result.return_code:
            logger.success()
        else:
            if retries:
                self.wait(
                    resource=resource,
                    labels=labels,
                    condition=condition,
                    timeout=timeout,
                    retries=retries - 1,
                    is_retry=True,
                )
            else:
                logger.std(result, raise_exception=True)

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
            f'--namespace="{namespace}"',
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
        os_command = ["kubectl", "get", resource, f'--namespace="{namespace}"']

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
