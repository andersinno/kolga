import shutil
import tempfile
from base64 import b64encode
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import colorful as cf
import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.models.events_v1_event import EventsV1Event
from kubernetes.client.models.events_v1_event_list import EventsV1EventList
from kubernetes.client.rest import ApiException
from tabulate import tabulate

from kolga.libs.helm import Helm
from kolga.libs.project import Project
from kolga.libs.service import Service
from kolga.settings import settings
from kolga.utils.exceptions import (
    DeploymentFailed,
    ImproperlyConfigured,
    NoClusterConfigError,
)
from kolga.utils.general import (
    camel_case_split,
    current_datetime_kubernetes_label_safe,
    get_deploy_name,
    get_environment_vars_by_prefix,
    kubernetes_safe_name,
    loads_json,
    run_os_command,
    validate_file_secret_path,
)
from kolga.utils.kube_logger import KubeLoggerThread
from kolga.utils.logger import logger
from kolga.utils.models import (
    BasicAuthUser,
    HelmValues,
    ReleaseStatus,
    SubprocessResult,
)


class _Monitoring(TypedDict, total=False):
    enabled: bool
    namespace: str
    path: str
    port: int


class _Pvc(TypedDict, total=False):
    accessMode: str
    enabled: bool
    mountPath: str
    size: str
    storageClass: str


class _Hpa(TypedDict, total=False):
    enabled: bool
    minReplicas: int
    maxReplicas: int
    avgCpuUtilization: int
    avgRamUtilization: int


class _Application(TypedDict, total=False):
    database_host: str
    database_url: str
    fileSecretName: str
    fileSecretPath: str
    initializeCommand: str
    livenessFile: str
    livenessPath: str
    migrateCommand: str
    monitoring: _Monitoring
    probeFailureThreshold: int
    probeInitialDelay: int
    probePeriod: int
    livenessProbeTimeout: int
    readinessProbeTimeout: int
    pvc: _Pvc
    readinessFile: str
    readinessPath: str
    requestCpu: str
    requestRam: str
    limitCpu: str
    limitRam: str
    secretName: str
    temporaryStoragePath: str
    track: str


class _Deployment(TypedDict, total=False):
    timestamp: str


class _GitLab(TypedDict, total=False):
    app: str
    env: str


class _Ingress(TypedDict, total=False):
    annotations: Dict[str, str]
    basicAuthSecret: str
    certManagerAnnotationPrefix: str
    clusterIssuer: str
    disabled: bool
    maxBodySize: str
    path: str
    preventRobots: bool
    secretName: str
    whitelistIP: str


class _Service(TypedDict, total=False):
    targetPort: int
    url: str
    urls: List[str]


class ApplicationDeploymentValues(HelmValues, total=False):
    application: _Application
    deployment: _Deployment
    gitlab: _GitLab
    hpa: _Hpa
    image: str
    ingress: _Ingress
    jobsOnly: bool
    namespace: str
    releaseOverride: str
    replicaCount: int
    service: _Service


old_init = k8s_client.Configuration.__init__


def new_init(self: k8s_client.Configuration, *k: Any, **kw: Any) -> None:
    old_init(self, *k, **kw)
    self.client_side_validation = False


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
        # Need to monkey patch configuration to disable client side validation that fails Event fetching
        # https://github.com/kubernetes-client/python/issues/1616
        k8s_client.Configuration.__init__ = new_init

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
            icon=f"{self.ICON}  🔑", message=f"Using {method} for Kubernetes auth"
        )

        config = k8s_client.Configuration()
        k8s_config.load_kube_config(client_configuration=config, config_file=kubeconfig)

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
            logger.info(
                title=f"{cf.yellow}{cf.bold}{reason}{cf.reset}",
                message=f" ({error.status} {cf.italic}{error_body['message'].capitalize()}{cf.reset})",
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
    def _b64_encode_file(path: Path) -> str:
        with open(str(path), "rb") as file:
            encoded_file = b64encode(file.read()).decode("UTF-8")
        return encoded_file

    @staticmethod
    def get_helm_path() -> Path:
        application_path = Path(settings.PROJECT_DIR)
        helm_path = application_path / "helm"
        auto_helm_path = settings.devops_root_path / "helm"
        if not helm_path.exists() and auto_helm_path.exists():
            shutil.copytree(auto_helm_path, helm_path)
        elif not helm_path.exists():
            logger.error(
                message="Could not find Helm chart to use",
                error=OSError(),
                raise_exception=True,
            )
        return helm_path

    @staticmethod
    def get_namespace_labels() -> Dict[str, str]:
        # TODO: Un-hardcode this label
        labels = {"app": "kubed"}

        if settings.K8S_POD_SECURITY:
            if settings.K8S_POD_SECURITY not in (
                "privileged",
                "baseline",
                "restricted",
            ):
                logger.warning(
                    f"Unknown pod security standard: {settings.K8S_POD_SECURITY}"
                )
            labels["pod-security.kubernetes.io/enforce"] = settings.K8S_POD_SECURITY

        if settings.PROJECT_ID:
            labels["kolga.io/project_id"] = settings.PROJECT_ID

        return labels

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
        logger.info(
            icon=f"{self.ICON}  🔨", title=f"Checking namespace {namespace}: ", end=""
        )

        try:
            v1.read_namespace(name=namespace)
        except ApiException as e:
            self._handle_api_error(e)
            if e.status != 404:
                raise e
        else:
            logger.success()
            return namespace

        v1_metadata = k8s_client.V1ObjectMeta(
            labels=self.get_namespace_labels(),
            name=namespace,
        )
        v1_namespace = k8s_client.V1Namespace(metadata=v1_metadata)
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
        namespace: str,
        track: str,
        project: Project,
        secret_name: str,
        encode: bool = True,
    ) -> None:
        deploy_name = get_deploy_name(track=track, postfix=project.name)
        v1 = k8s_client.CoreV1Api(self.client)
        v1_metadata = k8s_client.V1ObjectMeta(
            name=secret_name, namespace=namespace, labels={"release": deploy_name}
        )

        if encode:
            encoded_data = self._encode_secret(data)
        else:
            encoded_data = data

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

    def create_file_secrets_from_environment(
        self,
        namespace: str,
        track: str,
        project: Project,
        secret_name: str,
    ) -> Dict[str, str]:
        filesecrets = get_environment_vars_by_prefix(
            prefix=settings.K8S_FILE_SECRET_PREFIX
        )

        secrets, filename_mapping = self._parse_file_secrets(filesecrets)
        self.create_secret(
            data=secrets,
            encode=False,
            namespace=namespace,
            secret_name=secret_name,
            track=track,
            project=project,
        )

        return filename_mapping

    def _parse_file_secrets(
        self, filesecrets: Dict[str, str]
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        if settings.active_ci:
            valid_prefixes = settings.active_ci.VALID_FILE_SECRET_PATH_PREFIXES
        else:
            raise ImproperlyConfigured("An active CI is needed")

        filecontents = {}
        mapping = {}
        for name, filename in filesecrets.items():
            path = Path(filename)
            if not validate_file_secret_path(path, valid_prefixes):
                # TODO: This needs refactoring. Variable names do not match the contents.

                # If path-variable doesn't contain a valid path, we expect it to contain
                # the value for the secret file and we can use it directly.
                logger.warning(
                    f'Not a valid file path for a file "{name}". Using contents as a secret value.'
                )
                # Here we expect that filename-variable contains the secret
                filecontents[name] = b64encode(filename.encode("UTF-8")).decode("UTF-8")
                mapping[name] = f"{settings.K8S_FILE_SECRET_MOUNTPATH}/{name}"
                continue
            try:
                filecontents[name] = self._b64_encode_file(path)
                mapping[name] = f"{settings.K8S_FILE_SECRET_MOUNTPATH}/{name}"
            except OSError as e:
                logger.error(f'Error while reading a file: "{path}"', error=e)

        return filecontents, mapping

    def setup_helm(self) -> None:
        self.helm.setup_helm()

    def _create_basic_auth_data(
        self, basic_auth_users: List[BasicAuthUser] = settings.K8S_INGRESS_BASIC_AUTH
    ) -> Dict[str, str]:
        """
        Create secret data from list of `BasicAuthUser`

        The user credentials from the list of users will be encrypted and added
        to a temporary file using the `htpasswd` tool from Apache. The file is
        then read and base64 encoded (as required by Kubernetes secrets).

        Args:
            basic_auth_users: List of `BasicAuthUser` objects

        Returns:
            A dict with the key `auth` and base64 content of a htpasswd file as value
        """
        logger.info(
            icon=f"{self.ICON}  🔨", title="Generating basic auth data: ", end=""
        )

        if not basic_auth_users:
            return {}

        with tempfile.NamedTemporaryFile() as f:
            passwd_path = Path(f.name)
            for i, user in enumerate(basic_auth_users):
                os_command = ["htpasswd", "-b"]
                if i == 0:
                    os_command.append("-c")
                os_command += [str(passwd_path), user.username, user.password]
                result = run_os_command(os_command)
                if result.return_code:
                    logger.error(
                        message="The 'htpasswd' command failed to create an entry",
                        raise_exception=True,
                    )
            encoded_file = self._b64_encode_file(passwd_path)

        logger.success()
        logger.info(
            message=f"\t {len(settings.K8S_INGRESS_BASIC_AUTH)} users will be added to basic auth"
        )

        return {"auth": encoded_file}

    def create_basic_auth_secret(
        self, namespace: str, track: str, project: Project
    ) -> None:
        if not project.basic_auth_data:
            return None

        secret_data = self._create_basic_auth_data(project.basic_auth_data)
        secret_name = project.basic_auth_secret_name
        self.create_secret(
            data=secret_data,
            namespace=namespace,
            track=track,
            secret_name=secret_name,
            encode=False,
            project=project,
        )

    def deploy_service(self, service: "Service", namespace: str, track: str) -> None:
        deploy_name = get_deploy_name(track=track, postfix=service.name)

        with settings.plugin_manager.lifecycle.service_deployment(
            namespace=namespace, service=service, track=track
        ):
            self.helm.upgrade_chart(
                chart=service.chart,
                chart_path=service.chart_path,
                name=deploy_name,
                namespace=namespace,
                values=service.values,
                values_files=service.values_files,
                version=service.chart_version,
            )

    def get_application_deployment_values(
        self,
        namespace: str,
        project: Project,
        track: str,
    ) -> ApplicationDeploymentValues:
        values: ApplicationDeploymentValues = {
            "application": {
                "initializeCommand": project.initialize_command,
                "migrateCommand": project.migrate_command,
                "monitoring": {
                    "enabled": settings.K8S_MONITORING_ENABLED,
                    "path": settings.K8S_MONITORING_PATH,
                    "port": settings.K8S_MONITORING_PORT
                    if settings.K8S_MONITORING_PORT
                    else project.service_port,
                    "namespace": settings.K8S_MONITORING_NAMESPACE,
                },
                "probeFailureThreshold": project.probe_failure_threshold,
                "probeInitialDelay": project.probe_initial_delay,
                "probePeriod": project.probe_period,
                "livenessProbeTimeout": project.liveness_probe_timeout,
                "readinessProbeTimeout": project.readiness_probe_timeout,
                "livenessPath": project.liveness_path,
                "readinessPath": project.readiness_path,
                "secretName": project.secret_name,
                "track": track,
            },
            "deployment": {
                "timestamp": current_datetime_kubernetes_label_safe(),
            },
            "image": project.image,
            "ingress": {
                "maxBodySize": settings.K8S_INGRESS_MAX_BODY_SIZE,
                "secretName": project.ingress_secret_name,
            },
            "jobsOnly": settings.KOLGA_JOBS_ONLY,
            "namespace": namespace,
            "releaseOverride": f"{settings.ENVIRONMENT_SLUG}-{kubernetes_safe_name(project.name)}",
            "replicaCount": project.replica_count,
            "service": {
                "targetPort": project.service_port,
                "url": project.url,
                "urls": [project.url, *project.additional_urls],
            },
        }

        if str(settings.active_ci) == "GitLab CI":
            values["gitlab"] = {
                "app": settings.PROJECT_PATH_SLUG,
                "env": settings.ENVIRONMENT_SLUG,
            }

        if project.basic_auth_secret_name:
            values["ingress"]["basicAuthSecret"] = project.basic_auth_secret_name

        if project.file_secret_name:
            values["application"]["fileSecretName"] = project.file_secret_name
            values["application"]["fileSecretPath"] = settings.K8S_FILE_SECRET_MOUNTPATH

        if settings.K8S_PERSISTENT_STORAGE:
            values["application"]["pvc"] = {
                "accessMode": settings.K8S_PERSISTENT_STORAGE_ACCESS_MODE,
                "enabled": settings.K8S_PERSISTENT_STORAGE,
                "mountPath": settings.K8S_PERSISTENT_STORAGE_PATH,
                "size": settings.K8S_PERSISTENT_STORAGE_SIZE,
                "storageClass": settings.K8S_PERSISTENT_STORAGE_STORAGE_TYPE,
            }

        if project.request_cpu:
            values["application"]["requestCpu"] = project.request_cpu

        if project.request_ram:
            values["application"]["requestRam"] = project.request_ram

        if project.limit_cpu:
            values["application"]["limitCpu"] = project.limit_cpu

        if project.limit_ram:
            values["application"]["limitRam"] = project.limit_ram

        if project.temp_storage_path:
            values["application"]["temporaryStoragePath"] = project.temp_storage_path

        cert_issuer = self.get_certification_issuer(track=track)
        if cert_issuer:
            values["ingress"]["clusterIssuer"] = cert_issuer

        if settings.K8S_CERTMANAGER_USE_OLD_API:
            values["ingress"]["certManagerAnnotationPrefix"] = "certmanager.k8s.io"

        if settings.K8S_INGRESS_PATH:
            values["ingress"]["path"] = settings.K8S_INGRESS_PATH

        if settings.K8S_INGRESS_PREVENT_ROBOTS:
            values["ingress"]["preventRobots"] = True

        if settings.K8S_INGRESS_DISABLED:
            values["ingress"]["disabled"] = True

        if settings.K8S_INGRESS_WHITELIST_IPS:
            values["ingress"]["whitelistIP"] = settings.K8S_INGRESS_WHITELIST_IPS

        if settings.K8S_INGRESS_ANNOTATIONS:
            values["ingress"]["annotations"] = {}
            for annotation in settings.K8S_INGRESS_ANNOTATIONS:
                key, value = annotation.split("=", 1)
                values["ingress"]["annotations"][key] = value

        if settings.K8S_LIVENESS_FILE:
            values["application"]["livenessFile"] = settings.K8S_LIVENESS_FILE

        if settings.K8S_READINESS_FILE:
            values["application"]["readinessFile"] = settings.K8S_READINESS_FILE

        if settings.K8S_HPA_ENABLED:
            values["hpa"] = {
                "enabled": settings.K8S_HPA_ENABLED,
                "minReplicas": settings.K8S_HPA_MIN_REPLICAS,
                "maxReplicas": settings.K8S_HPA_MAX_REPLICAS,
            }
            if settings.K8S_HPA_MAX_CPU_AVG:
                values["hpa"]["avgCpuUtilization"] = settings.K8S_HPA_MAX_CPU_AVG
            if settings.K8S_HPA_MAX_RAM_AVG:
                values["hpa"]["avgRamUtilization"] = settings.K8S_HPA_MAX_RAM_AVG

        return values

    def create_application_deployment(
        self,
        namespace: str,
        project: Project,
        track: str,
    ) -> None:
        pod_events: str = ""
        helm_path = self.get_helm_path()
        values = self.get_application_deployment_values(
            namespace=namespace,
            project=project,
            track=track,
        )

        application_labels = {
            "deploymentTime": values["deployment"]["timestamp"],
            "release": project.deploy_name,
            "track": track,
        }
        log_collector = KubeLoggerThread(
            labels=application_labels,
            namespace=namespace,
        )

        with settings.plugin_manager.lifecycle.project_deployment(
            namespace=namespace, project=project, track=track
        ):
            log_collector.start()
            result = self.helm.upgrade_chart(
                chart_path=helm_path,
                name=project.deploy_name,
                namespace=namespace,
                values=values,
                raise_exception=False,
            )
            try:
                v1 = k8s_client.EventsV1Api(self.client)
                response: EventsV1EventList = v1.list_namespaced_event(namespace)
                events: List[List[str]] = []
                event: EventsV1Event
                for event in response.items:
                    events.append(
                        [
                            event.deprecated_first_timestamp.strftime("%H:%M:%S"),
                            f"{event.regarding.kind}/{event.regarding.name}",
                            event.reason,
                            event.note,
                        ]
                    )
                pod_events = tabulate(
                    events,
                    headers=["Timestamp", "Object", "Reason", "Message"],
                    tablefmt="orgtbl",
                )

            except ApiException as e:
                logger.debug(
                    "Exception when calling EventsV1beta1Api->list_namespaced_event: %s\n"
                    % e
                )
            except Exception as e:
                logger.debug("Getting events failed, ignoring: %s\n" % e)

            log_collector.stop()

            if result.return_code:
                logger.info(
                    icon=f"{self.ICON} 🏷️",
                    title="Deployment values (without environment vars):",
                )
                for line in yaml.dump(values).split("\n"):
                    logger.info(message=f"\t{line}")

                status = self.status(namespace=namespace, labels=application_labels)
                logger.info(message=str(status))

                logger.info(
                    icon=f"{self.ICON}  📋️️ ",
                    title="Getting events for resource: ",
                )

                logger.info(pod_events)

                logger.info(
                    icon=f"{self.ICON}  📋️️ ",
                    title="Getting logs for resource: ",
                )
                with log_collector.log_path.open() as f:
                    for line in f:
                        logger.info(line, end="")

                raise DeploymentFailed()

        if not settings.K8S_INGRESS_DISABLED:
            logger.info(
                icon=f"{self.ICON}  📄",
                title=f"Deployment can be accessed via {project.url}",
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
            "--ignore-not-found",
            "--wait=true",
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
        result = run_os_command(os_command, shell=True)  # nosec
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

    def _resource_command(
        self,
        resource: str,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        namespace: str = settings.K8S_NAMESPACE,
    ) -> List[str]:
        command_args = [resource, f"--namespace={namespace}"]
        if labels:
            labels_str = self.labels_to_string(labels)
            command_args += ["-l", labels_str]
            logger.info(title=f" with labels {labels_str}", end="")
        if name:
            command_args += [name]
            logger.info(title=f" with name '{name}'", end="")
        return command_args

    def get_certification_issuer(self, track: str) -> Optional[str]:
        logger.info(
            icon=f"{self.ICON} 🏵️️", title="Checking certification issuer", end=""
        )

        raise_exception = False
        if settings.K8S_CLUSTER_ISSUER:
            cert_issuer: str = settings.K8S_CLUSTER_ISSUER
            logger.info(message=" (settings): ", end="")
            raise_exception = True
        else:
            cert_issuer = f"certificate-letsencrypt-{track}"
            logger.info(message=" (track): ", end="")

        os_command = ["kubectl", "get", "clusterissuer", cert_issuer]
        result = run_os_command(os_command, shell=True)  # nosec
        if not result.return_code:
            logger.success(message=cert_issuer)
            return cert_issuer
        else:
            error_message = f'No issuer "{cert_issuer}" found, using cluster defaults'
            if raise_exception:
                logger.error(message=error_message, raise_exception=True)
            else:
                logger.info(message=error_message)
            return None

    def get(
        self,
        resource: str,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        namespace: str = settings.K8S_NAMESPACE,
        raise_exception: bool = True,
    ) -> SubprocessResult:
        os_command = ["kubectl", "get"]

        logger.info(icon=f"{self.ICON}  ℹ️ ", title=f"Getting {resource}", end="")
        os_command += self._resource_command(
            resource=resource, name=name, labels=labels, namespace=namespace
        )
        logger.info(": ", end="")
        result = run_os_command(os_command, shell=True)  # nosec
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=raise_exception)
        return result

    def status(
        self,
        labels: Optional[Dict[str, str]] = None,
        namespace: str = settings.K8S_NAMESPACE,
    ) -> ReleaseStatus:
        deployment_status = self.get(
            resource="deployments",
            labels=labels,
            namespace=namespace,
            raise_exception=False,
        )

        pods_status = self.get(
            resource="pods", labels=labels, namespace=namespace, raise_exception=False
        )

        return ReleaseStatus(deployment=deployment_status.out, pods=pods_status.out)
