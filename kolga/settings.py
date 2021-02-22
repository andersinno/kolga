import json
import os
import sys
import tempfile
import uuid
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pluggy  # type: ignore
from environs import Env

from kolga.utils.logger import logger
from kolga.utils.models import BasicAuthUser

from .hooks.exceptions import PluginMissingConfiguration
from .hooks.hookspec import KolgaHookSpec
from .plugins import KOLGA_CORE_PLUGINS
from .utils.environ_parsers import basicauth_parser, list_none_parser
from .utils.exceptions import NoClusterConfigError
from .utils.general import deep_get, kubernetes_safe_name

service_artifacts_folder = os.environ.get("SERVICE_ARTIFACT_FOLDER", None)
build_artifacts_folder = os.environ.get("BUILD_ARTIFACT_FOLDER", None)
env_files = []
if service_artifacts_folder:
    env_files.extend(glob(f"./{service_artifacts_folder}/*.env"))
if build_artifacts_folder:
    env_files.extend(glob(f"./{build_artifacts_folder}/*.env"))

env = Env()

env.add_parser("basicauth", basicauth_parser)
env.add_parser("list_none", list_none_parser)
env.read_env()
for env_file in env_files:
    env.read_env(env_file)

PROJECT_NAME_VAR = "PROJECT_NAME"

# TODO Investigate further if we can have only one definition
#      list and keep type definitions.
_VARIABLE_DEFINITIONS: Dict[str, List[Any]] = {
    # ================================================
    # PROJECT
    # ================================================
    PROJECT_NAME_VAR: [env.str, ""],
    "PROJECT_DIR": [env.str, ""],
    "PROJECT_ID": [env.str, ""],
    "PROJECT_PATH_SLUG": [env.str, ""],
    # ================================================
    # DOCKER
    # ================================================
    "BUILDKIT_CACHE_IMAGE_NAME": [env.str, "cache"],
    "BUILDKIT_CACHE_REPO": [env.str, ""],
    "BUILDKIT_CACHE_DISABLE": [env.bool, False],
    "CONTAINER_REGISTRY": [env.str, "docker.anders.fi"],
    "CONTAINER_REGISTRY_PASSWORD": [env.str, ""],
    "CONTAINER_REGISTRY_REPO": [env.str, ""],
    "CONTAINER_REGISTRY_USER": [env.str, ""],
    "BUILT_DOCKER_TEST_IMAGE": [env.str, ""],
    "DOCKER_BUILD_ARG_PREFIX": [env.str, "DOCKER_BUILD_ARG_"],
    "DOCKER_BUILD_CONTEXT": [env.str, "."],
    "DOCKER_BUILD_SOURCE": [env.str, "Dockerfile"],
    "DOCKER_HOST": [env.str, ""],
    "DOCKER_IMAGE_NAME": [env.str, ""],
    "DOCKER_TEST_IMAGE_STAGE": [env.str, "development"],
    # ================================================
    # ENVIRONMENT
    # ================================================
    "DEFAULT_TRACK": [env.str, "stable"],
    "ENVIRONMENT_SLUG": [env.str, ""],
    "ENVIRONMENT_URL": [env.str, ""],
    "SERVICE_PORT": [env.int, 8000],
    # ================================================
    # GIT
    # ================================================
    "GIT_COMMIT_REF_NAME": [env.str, ""],
    "GIT_COMMIT_SHA": [env.str, ""],
    "GIT_DEFAULT_TARGET_BRANCH": [env.str, "master"],
    "GIT_TARGET_BRANCH": [env.str, ""],
    # ================================================
    # APPLICATION
    # ================================================
    "APP_INITIALIZE_COMMAND": [env.str, ""],
    "APP_MIGRATE_COMMAND": [env.str, ""],
    "BUILD_ARTIFACT_FOLDER": [env.str, ""],
    "DATABASE_DB": [env.str, "appdb"],
    "DATABASE_PASSWORD": [env.str, str(uuid.uuid4())],
    "DATABASE_USER": [env.str, "user"],
    "MYSQL_VERSION_TAG": [env.str, "5.7"],
    "POSTGRES_IMAGE": [env.str, "docker.io/bitnami/postgresql:9.6"],
    "RABBITMQ_VERSION_TAG": [env.str, "3.8.5"],
    "SERVICE_ARTIFACT_FOLDER": [env.str, ""],
    # ================================================
    # KUBERNETES
    # ================================================
    "K8S_ADDITIONAL_HOSTNAMES": [env.list_none, []],
    "K8S_CLUSTER_ISSUER": [env.str, ""],
    "K8S_HPA_ENABLED": [env.bool, False],
    "K8S_HPA_MAX_REPLICAS": [env.int, 3],
    "K8S_HPA_MIN_REPLICAS": [env.int, 1],
    "K8S_HPA_MAX_CPU_AVG": [env.int, 75],
    "K8S_HPA_MAX_RAM_AVG": [env.int, 0],
    "K8S_INGRESS_ANNOTATIONS": [env.list_none, []],
    "K8S_INGRESS_BASE_DOMAIN": [env.str, ""],
    "K8S_INGRESS_BASIC_AUTH": [env.basicauth, []],
    "K8S_INGRESS_DISABLED": [env.bool, False],
    "K8S_CERTMANAGER_USE_OLD_API": [env.bool, False],
    "K8S_INGRESS_MAX_BODY_SIZE": [env.str, "100m"],
    "K8S_INGRESS_PREVENT_ROBOTS": [env.bool, False],
    "K8S_INGRESS_SECRET_NAME": [env.str, ""],
    "K8S_INGRESS_WHITELIST_IPS": [env.str, ""],
    "K8S_LIVENESS_PATH": [env.str, "/healthz"],
    "K8S_NAMESPACE": [env.str, ""],
    "K8S_PROBE_FAILURE_THRESHOLD": [env.int, 3],
    "K8S_PROBE_INITIAL_DELAY": [env.int, 60],
    "K8S_PROBE_PERIOD": [env.int, 10],
    "K8S_FILE_SECRET_MOUNTPATH": [env.str, "/tmp/secrets"],  # nosec
    "K8S_FILE_SECRET_PREFIX": [env.str, "K8S_FILE_SECRET_"],
    "K8S_READINESS_PATH": [env.str, "/readiness"],
    "K8S_REQUEST_CPU": [env.str, "50m"],
    "K8S_REQUEST_RAM": [env.str, "128Mi"],
    "K8S_LIMIT_CPU": [env.str, ""],
    "K8S_LIMIT_RAM": [env.str, ""],
    "K8S_SECRET_PREFIX": [env.str, "K8S_SECRET_"],
    "K8S_LIVENESS_FILE": [env.str, ""],
    "K8S_PERSISTENT_STORAGE": [env.bool, False],
    "K8S_PERSISTENT_STORAGE_ACCESS_MODE": [env.str, "ReadWriteOnce"],
    "K8S_PERSISTENT_STORAGE_PATH": [env.str, ""],
    "K8S_PERSISTENT_STORAGE_SIZE": [env.str, "1Gi"],
    "K8S_PERSISTENT_STORAGE_STORAGE_TYPE": [env.str, "standard"],
    "K8S_READINESS_FILE": [env.str, ""],
    "K8S_REPLICACOUNT": [env.int, 1],
    "K8S_TEMP_STORAGE_PATH": [env.str, ""],
    "KUBECONFIG": [env.str, ""],
    "DEPENDS_ON_PROJECTS": [env.str, ""],
    # ================================================
    # PIPELINE
    # ================================================
    "KOLGA_JOBS_ONLY": [env.bool, False],
    # ================================================
    # VAULT
    # ================================================
    "VAULT_ADDR": [env.str, ""],
    "VAULT_JWT_AUTH_PATH": [env.str, "jwt"],
    "VAULT_KV_SECRET_MOUNT_POINT": [env.str, "secrets"],
    "VAULT_JWT": [env.str, ""],
    "VAULT_TLS_ENABLED": [env.bool, True],
    # ================================================
    # JOB
    # ================================================
    "JOB_ACTOR": [env.str, ""],
    # ================================================
    # MERGE/PULL-REQUEST
    # ================================================
    "PR_ASSIGNEES": [env.str, ""],
    "PR_ID": [env.str, ""],
    "PR_TITLE": [env.str, ""],
    "PR_URL": [env.str, ""],
}


class Settings:
    PROJECT_NAME: str
    PROJECT_DIR: str
    PROJECT_ID: str
    PROJECT_PATH_SLUG: str
    BUILDKIT_CACHE_IMAGE_NAME: str
    BUILDKIT_CACHE_REPO: str
    BUILDKIT_CACHE_DISABLE: bool
    CONTAINER_REGISTRY: str
    CONTAINER_REGISTRY_PASSWORD: str
    CONTAINER_REGISTRY_REPO: str
    CONTAINER_REGISTRY_USER: str
    BUILT_DOCKER_TEST_IMAGE: str
    DOCKER_BUILD_ARG_PREFIX: str
    DOCKER_BUILD_CONTEXT: str
    DOCKER_BUILD_SOURCE: str
    DOCKER_HOST: str
    DOCKER_IMAGE_NAME: str
    DOCKER_TEST_IMAGE_STAGE: str
    DEFAULT_TRACK: str
    ENVIRONMENT_SLUG: str
    ENVIRONMENT_URL: str
    SERVICE_PORT: str
    GIT_COMMIT_REF_NAME: str
    GIT_COMMIT_SHA: str
    GIT_DEFAULT_TARGET_BRANCH: str
    GIT_TARGET_BRANCH: str
    APP_INITIALIZE_COMMAND: str
    APP_MIGRATE_COMMAND: str
    BUILD_ARTIFACT_FOLDER: str
    DATABASE_DB: str
    DATABASE_PASSWORD: str
    DATABASE_USER: str
    MYSQL_VERSION_TAG: str
    POSTGRES_IMAGE: str
    RABBITMQ_VERSION_TAG: str
    SERVICE_ARTIFACT_FOLDER: str
    K8S_ADDITIONAL_HOSTNAMES: List[str]
    K8S_CLUSTER_ISSUER: str
    K8S_HPA_ENABLED: bool
    K8S_HPA_MAX_REPLICAS: int
    K8S_HPA_MIN_REPLICAS: int
    K8S_HPA_MAX_CPU_AVG: int
    K8S_HPA_MAX_RAM_AVG: int
    K8S_INGRESS_ANNOTATIONS: List[str]
    K8S_INGRESS_BASE_DOMAIN: str
    K8S_INGRESS_BASIC_AUTH: List[BasicAuthUser]
    K8S_INGRESS_DISABLED: bool
    K8S_CERTMANAGER_USE_OLD_API: bool
    K8S_INGRESS_MAX_BODY_SIZE: str
    K8S_INGRESS_PREVENT_ROBOTS: bool
    K8S_INGRESS_SECRET_NAME: str
    K8S_INGRESS_WHITELIST_IPS: str
    K8S_LIVENESS_PATH: str
    K8S_NAMESPACE: str
    K8S_PERSISTENT_STORAGE: bool
    K8S_PERSISTENT_STORAGE_ACCESS_MODE: str
    K8S_PERSISTENT_STORAGE_PATH: str
    K8S_PERSISTENT_STORAGE_SIZE: str
    K8S_PERSISTENT_STORAGE_STORAGE_TYPE: str
    K8S_PROBE_FAILURE_THRESHOLD: int
    K8S_PROBE_INITIAL_DELAY: int
    K8S_PROBE_PERIOD: int
    K8S_FILE_SECRET_MOUNTPATH: str
    K8S_FILE_SECRET_PREFIX: str
    K8S_READINESS_PATH: str
    K8S_REQUEST_CPU: str
    K8S_REQUEST_RAM: str
    K8S_LIMIT_CPU: str
    K8S_LIMIT_RAM: str
    K8S_SECRET_PREFIX: str
    K8S_LIVENESS_FILE: str
    K8S_READINESS_FILE: str
    K8S_REPLICACOUNT: int
    K8S_TEMP_STORAGE_PATH: str
    KUBECONFIG: str
    DEPENDS_ON_PROJECTS: str
    KOLGA_JOBS_ONLY: bool
    VAULT_ADDR: str
    VAULT_JWT_AUTH_PATH: str
    VAULT_KV_SECRET_MOUNT_POINT: str
    VAULT_TLS_ENABLED: bool
    VAULT_JWT: str
    JOB_ACTOR: str
    PR_ASSIGNEES: str
    PR_ID: str
    PR_TITLE: str
    PR_URL: str

    def __init__(self) -> None:
        missing_vars = _VARIABLE_DEFINITIONS.keys() - self.__annotations__.keys()
        if missing_vars:
            raise AssertionError(
                f"Not all env variables are set class attributes ({missing_vars})"
            )

        self.devops_root_path = Path(sys.argv[0]).resolve().parent

        self.active_ci: Optional[Any] = None
        self.supported_cis: List[Any] = [
            GitLabMapper(),
            AzurePipelinesMapper(),
            GitHubActionsMapper(),
        ]
        self._set_ci_environment()
        setattr(self, PROJECT_NAME_VAR, self._get_project_name())

        if self.active_ci:
            self._map_ci_variables()

        self._set_attributes()

        self.plugin_manager = self._setup_pluggy()

    def _setup_pluggy(self) -> pluggy.PluginManager:
        pm: pluggy.PluginManager = pluggy.PluginManager("kolga")
        pm.add_hookspecs(KolgaHookSpec)

        return pm

    def load_plugins(self) -> None:
        loading_plugins = False

        for plugin in KOLGA_CORE_PLUGINS:
            plugin_loaded, message = self._load_plugin(plugin)
            if not loading_plugins and plugin_loaded:
                logger.info(
                    icon="🔌",
                    title="Loading plugins:",
                )
                loading_plugins = True
            if plugin_loaded:
                logger.info(f"{plugin.verbose_name}: {message}")
            # TODO: Implement verbose logging where the plugin loading error would be shown

    def _load_plugin(self, plugin: Any) -> Tuple[bool, str]:
        try:
            self.plugin_manager.register(plugin(env), name=plugin.name)
        except PluginMissingConfiguration as e:
            return False, f"⚠️  {e}"
        return True, "✅"

    def _unload_plugin(self, plugin: Any) -> Any:
        # We need to first fetch the instance of the plugin in order to unregister it.
        # If we do not do this, Pluggy will not properly unregister as it will try
        # to do it on the class and not the instance, which will not hard-fail, but
        # will only partially unregister the plugin, leaving it still to be called
        # by hooks.
        _to_be_unregistered_plugin = self.plugin_manager.get_plugin(plugin.name)

        return self.plugin_manager.unregister(_to_be_unregistered_plugin)

    def _set_attributes(self) -> None:
        """
        Read and set settings from environment variables

        Strategy:
        1. If a value is set in the environment, use it
        2. If a value is set in a project prefixed environment variable use it
        3. If the attribute is already set, use the pre-existing value
        4. Should all else fail, use the default value
        """
        from .utils.general import env_var_safe_key

        safe_name = env_var_safe_key(self.PROJECT_NAME)
        for variable, (parser, default_value) in _VARIABLE_DEFINITIONS.items():
            value = parser(variable, None)
            if value is None:
                project_prefixed_variable_name = f"{safe_name}_{variable}"
                value = parser(project_prefixed_variable_name, None)

            if value is None:
                if hasattr(self, variable):
                    # Don't override an already-set value with default
                    continue
                else:
                    value = default_value

            setattr(self, variable, value)

    def _set_ci_environment(self) -> None:
        for ci in self.supported_cis:
            if ci.is_active:
                self.active_ci = ci
                ci.initialize()
                break

    def _get_project_name(self) -> str:
        parser, default_value = _VARIABLE_DEFINITIONS[PROJECT_NAME_VAR]
        project_name: str = parser(PROJECT_NAME_VAR, default_value)

        if not project_name and self.active_ci:
            name_from = self.active_ci.MAPPING.get(PROJECT_NAME_VAR)
            if name_from:
                # TODO: Use parser and add support for generated properties
                project_name = os.environ.get(name_from, "")

        if not project_name:
            raise AssertionError("No project name could be found!")
        return project_name

    def _map_ci_variables(self) -> None:
        """
        Map CI variables to settings

        If the source name starts with '=', get the value from mapper's
        attribute. Otwerwise read the value from environment.
        """
        mapper = self.active_ci
        if not mapper:
            return None

        ci_value = None
        for name_to, name_from in mapper.MAPPING.items():
            if name_to not in _VARIABLE_DEFINITIONS:
                logger.warning(
                    message=f"CI variable mapping failed, no setting called {name_to}"
                )

            if name_from.startswith("="):
                name_from = name_from[1:]
                try:
                    ci_value = getattr(mapper, name_from)
                except AttributeError:
                    logger.error(
                        message=f"CI variable mapping failed, no mapper attribute called {name_from}"
                    )
            else:
                parser, _ = _VARIABLE_DEFINITIONS[name_to]
                ci_value = parser(name_from, None)

            if ci_value is not None:
                setattr(self, name_to, ci_value)

    def create_kubeconfig(self, track: str) -> Tuple[str, str]:
        """
        Create temporary kubernetes configuration based on contents of
        KUBECONFIG_RAW or KUBECONFIG_RAW_<track>.

        Args:
            track: Current deployment track

        Returns:
            A tuple of kubeconfig and the variable name that was used
        """
        name = ""
        key = ""

        possible_keys = ["KUBECONFIG_RAW"]
        if track:
            possible_keys.append(f"KUBECONFIG_RAW_{track.upper()}")

        for key in reversed(possible_keys):
            kubeconfig = os.environ.get(key, "")
            if not kubeconfig:
                continue

            fp, name = tempfile.mkstemp()
            with os.fdopen(fp, "w") as f:
                f.write(kubeconfig)
            break

            logger.info(message=f"Created a kubeconfig file using {key}")

        return name, key

    def setup_kubeconfig(self, track: str) -> Tuple[str, str]:
        """
        Point KUBECONFIG environment variable to the correct kubeconfig

        Uses a track-specific kubeconfig if `KUBECONFIG_{track}` is set.
        Otherwise does a fallback to `KUBECONFIG`.

        NOTE: This logic won't be needed once we can start using variables with
        environment scope. Currenty this is blocked by missing API in GitLab.

        Args:
            track: Current deployment track

        Returns:
            A tuple of kubeconfig and the variable name that was used


        """
        # Check if there is a configuration available in KUBECONFIG_RAW env variable
        kubeconfig, key = self.create_kubeconfig(track)

        if kubeconfig:
            os.environ["KUBECONFIG"] = kubeconfig
            return kubeconfig, key
        else:
            possible_keys = ["KUBECONFIG"]
            if track:
                possible_keys.append(f"KUBECONFIG_{track.upper()}")

            for key in reversed(possible_keys):
                kubeconfig = os.environ.get(key, "")
                if not kubeconfig:
                    continue

                self.KUBECONFIG = kubeconfig

                # Set `KUBECONFIG` environment variable for subsequent `kubectl` calls.
                os.environ["KUBECONFIG"] = kubeconfig

                return kubeconfig, key

        raise NoClusterConfigError()


class BaseCI:
    def initialize(self) -> None:
        pass


class AzurePipelinesMapper(BaseCI):
    MAPPING = {
        "DOCKER_IMAGE_NAME": "BUILD_DEFINITIONNAME",
        "GIT_COMMIT_REF_NAME": "BUILD_SOURCEBRANCHNAME",  # TODO: Do this programmatically instead
        "GIT_COMMIT_SHA": "BUILD_SOURCEVERSION",
        "PROJECT_ID": "BUILD_REPOSITORY_ID",
        "PROJECT_NAME": "SYSTEM_TEAMPROJECT",
    }

    def __str__(self) -> str:
        return "Azure Pipelines"

    @property
    def is_active(self) -> bool:
        return bool(env.str("AZURE_HTTP_USER_AGENT", ""))

    @property
    def VALID_FILE_SECRET_PATH_PREFIXES(self) -> List[str]:
        return ["/builds/"]


class GitLabMapper(BaseCI):
    MAPPING = {
        "CONTAINER_REGISTRY": "CI_REGISTRY",
        "CONTAINER_REGISTRY_PASSWORD": "CI_REGISTRY_PASSWORD",
        "CONTAINER_REGISTRY_REPO": "CI_REGISTRY_IMAGE",
        "CONTAINER_REGISTRY_USER": "CI_REGISTRY_USER",
        "ENVIRONMENT_SLUG": "CI_ENVIRONMENT_SLUG",
        "ENVIRONMENT_URL": "CI_ENVIRONMENT_URL",
        "GIT_COMMIT_REF_NAME": "CI_COMMIT_REF_NAME",
        "GIT_COMMIT_SHA": "CI_COMMIT_SHA",
        "GIT_DEFAULT_TARGET_BRANCH": "CI_DEFAULT_BRANCH",
        "GIT_TARGET_BRANCH": "CI_MERGE_REQUEST_TARGET_BRANCH_NAME",
        "JOB_ACTOR": "GITLAB_USER_NAME",
        "K8S_CLUSTER_ISSUER": "KUBE_CLUSTER_ISSUER",
        "K8S_INGRESS_BASE_DOMAIN": "KUBE_INGRESS_BASE_DOMAIN",
        "K8S_INGRESS_PREVENT_ROBOTS": "KUBE_INGRESS_PREVENT_ROBOTS",
        "K8S_NAMESPACE": "KUBE_NAMESPACE",
        "PR_ASSIGNEES": "CI_MERGE_REQUEST_ASSIGNEES",
        "PR_ID": "CI_MERGE_REQUEST_ID",
        "PROJECT_DIR": "CI_PROJECT_DIR",
        "PROJECT_ID": "CI_PROJECT_ID",
        "PROJECT_NAME": "CI_PROJECT_NAME",
        "PROJECT_PATH_SLUG": "CI_PROJECT_PATH_SLUG",
        "PR_TITLE": "CI_MERGE_REQUEST_TITLE",
        "PR_URL": "CI_MERGE_REQUEST_PROJECT_URL",
        "VAULT_JWT": "CI_JOB_JWT",
    }

    def __str__(self) -> str:
        return "GitLab CI"

    @property
    def is_active(self) -> bool:
        return env.bool("GITLAB_CI", False)  # type: ignore

    @property
    def VALID_FILE_SECRET_PATH_PREFIXES(self) -> List[str]:
        return ["/builds/"]


class GitHubActionsMapper(BaseCI):
    MAPPING = {
        "GIT_COMMIT_REF_NAME": "GITHUB_REF",
        "GIT_COMMIT_SHA": "GITHUB_SHA",
        "GIT_TARGET_BRANCH": "GITHUB_BASE_REF",
        "JOB_ACTOR": "GITHUB_ACTOR",
        "PR_ID": "=PR_ID",
        "PR_TITLE": "=PR_TITLE",
        "PR_URL": "=PR_URL",
        "PROJECT_ID": "=PROJECT_ID",
        "PROJECT_NAME": "GITHUB_REPOSITORY",
    }
    _EVENT_DATA: Optional[Dict[str, Any]]

    def __str__(self) -> str:
        return "GitHub Actions"

    def initialize(self) -> None:
        self._set_event_data_variables()

    @property
    def is_active(self) -> bool:
        return env.bool("GITHUB_ACTIONS", False)  # type: ignore

    @property
    def PR_ID(self) -> Optional[str]:
        if pr_url := deep_get(self._EVENT_DATA, "pull_request.number"):
            return str(pr_url)
        return None

    @property
    def PR_TITLE(self) -> Optional[str]:
        if pr_title := deep_get(self._EVENT_DATA, "pull_request.title"):
            return str(pr_title)
        return None

    @property
    def PR_URL(self) -> Optional[str]:
        if pr_number := deep_get(self._EVENT_DATA, "pull_request.url"):
            return str(pr_number)
        return None

    @property
    def PROJECT_ID(self) -> Optional[str]:
        repository = env.str("GITHUB_REPOSITORY", None)
        if not repository:
            return None
        return kubernetes_safe_name(repository)

    @property
    def VALID_FILE_SECRET_PATH_PREFIXES(self) -> List[str]:
        return ["/builds/"]

    def _set_event_data_variables(self) -> None:
        """
        Read event data from filesystem

        Events in GitHub has a lot of metadata, it is not exposed
        through environment variables however. This function takes the
        metadata, that is stored in a json file, parses it, and stores
        it in a member variable for later use.
        """
        event_data_path = env.path("GITHUB_EVENT_PATH", "")
        try:
            with event_data_path.open() as event_data_file:
                self._EVENT_DATA = json.load(event_data_file)
        except (FileNotFoundError, IOError, OSError, ValueError):
            self._EVENT_DATA = None


settings = Settings()
