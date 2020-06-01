import os
import sys
import uuid
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from environs import Env

from kolga.utils.logger import logger
from kolga.utils.models import BasicAuthUser

from .utils.environ_parsers import basicauth_parser, list_none_parser
from .utils.exceptions import NoClusterConfigError

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
    "PROJECT_PATH_SLUG": [env.str, ""],
    # ================================================
    # DOCKER
    # ================================================
    "BUILDKIT_CACHE_REPO": [env.str, "cache"],
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
    "K8S_INGRESS_BASE_DOMAIN": [env.str, ""],
    "K8S_INGRESS_BASIC_AUTH": [env.basicauth, []],
    "K8S_INGRESS_DISABLED": [env.bool, False],
    "K8S_CERTMANAGER_USE_OLD_API": [env.bool, False],
    "K8S_INGRESS_MAX_BODY_SIZE": [env.str, "100m"],
    "K8S_INGRESS_PREVENT_ROBOTS": [env.bool, False],
    "K8S_LIVENESS_PATH": [env.str, "/healthz"],
    "K8S_NAMESPACE": [env.str, ""],
    "K8S_PROBE_FAILURE_THRESHOLD": [env.int, 3],
    "K8S_PROBE_INITIAL_DELAY": [env.int, 60],
    "K8S_PROBE_PERIOD": [env.int, 10],
    "K8S_FILE_SECRET_MOUNTPATH": [env.str, "/tmp/secrets"],
    "K8S_FILE_SECRET_PREFIX": [env.str, "K8S_FILE_SECRET_"],
    "K8S_READINESS_PATH": [env.str, "/readiness"],
    "K8S_REQUEST_CPU": [env.str, ""],
    "K8S_REQUEST_RAM": [env.str, ""],
    "K8S_SECRET_PREFIX": [env.str, "K8S_SECRET_"],
    "K8S_LIVENESS_FILE": [env.str, ""],
    "K8S_READINESS_FILE": [env.str, ""],
    "K8S_REPLICACOUNT": [env.int, 1],
    "K8S_TEMP_STORAGE_PATH": [env.str, ""],
    "KUBECONFIG": [env.str, ""],
    "DEPENDS_ON_PROJECTS": [env.str, ""],
    # ================================================
    # PIPELINE
    # ================================================
    "KOLGA_JOBS_ONLY": [env.bool, False],
}


class Settings:
    PROJECT_NAME: str
    PROJECT_DIR: str
    PROJECT_PATH_SLUG: str
    BUILDKIT_CACHE_REPO: str
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
    K8S_INGRESS_BASE_DOMAIN: str
    K8S_INGRESS_BASIC_AUTH: List[BasicAuthUser]
    K8S_INGRESS_DISABLED: bool
    K8S_CERTMANAGER_USE_OLD_API: bool
    K8S_INGRESS_MAX_BODY_SIZE: str
    K8S_INGRESS_PREVENT_ROBOTS: bool
    K8S_LIVENESS_PATH: str
    K8S_NAMESPACE: str
    K8S_PROBE_FAILURE_THRESHOLD: int
    K8S_PROBE_INITIAL_DELAY: int
    K8S_PROBE_PERIOD: int
    K8S_FILE_SECRET_MOUNTPATH: str
    K8S_FILE_SECRET_PREFIX: str
    K8S_READINESS_PATH: str
    K8S_REQUEST_CPU: str
    K8S_REQUEST_RAM: str
    K8S_SECRET_PREFIX: str
    K8S_LIVENESS_FILE: str
    K8S_READINESS_FILE: str
    K8S_REPLICACOUNT: int
    K8S_TEMP_STORAGE_PATH: str
    KUBECONFIG: str
    DEPENDS_ON_PROJECTS: str
    KOLGA_JOBS_ONLY: bool

    def __init__(self) -> None:
        missing_vars = _VARIABLE_DEFINITIONS.keys() - self.__annotations__.keys()
        if missing_vars:
            raise AssertionError(
                f"Not all env variables are set class attributes ({missing_vars})"
            )

        self.devops_root_path = Path(sys.argv[0]).resolve().parent

        self.active_ci: Optional[Any] = None
        self.supported_cis: List[Any] = [GitLabMapper(), AzurePipelinesMapper()]
        self._set_ci_environment()
        setattr(self, PROJECT_NAME_VAR, self._get_project_name())

        self._set_attributes()

        if self.active_ci:
            self._map_ci_variables()

    def _set_attributes(self) -> None:
        from .utils.general import env_var_safe_key

        self.PROJECT_NAME_SAFE = env_var_safe_key(self.PROJECT_NAME)
        for variable, (parser, default_value) in _VARIABLE_DEFINITIONS.items():
            value = parser(variable, None)
            if value is None:
                project_prefixed_variable_name = f"{self.PROJECT_NAME_SAFE}_{variable}"
                value = parser(project_prefixed_variable_name, default_value)
            setattr(self, variable, value)

    def _set_ci_environment(self) -> None:
        for ci in self.supported_cis:
            if ci.is_active:
                self.active_ci = ci
                break

    def _get_project_name(self) -> str:
        parser, default_value = _VARIABLE_DEFINITIONS[PROJECT_NAME_VAR]
        project_name: str = parser(PROJECT_NAME_VAR, default_value)

        if not project_name and self.active_ci:
            for (name_from, name_to) in self.active_ci.MAPPING.items():
                if name_to == PROJECT_NAME_VAR:
                    project_name = os.environ.get(name_from, "")

        if not project_name:
            raise AssertionError("No project name could be found!")
        return project_name

    def _map_ci_variables(self) -> None:
        """
        Map CI variables to settings

        Strategy:
        1. If a value is set in the env, use it
        2. If a value is not set in the env and a CI value is set, use the CI value
        3. If a value is not set in the env and not in the CI, use the default value
        """
        if not self.active_ci:
            return None
        for name_from, name_to in self.active_ci.MAPPING.items():
            if name_to not in _VARIABLE_DEFINITIONS:
                logger.warning(
                    message=f"CI variable mapping failed, no setting called {name_to}"
                )

            has_set_value = name_to if name_to in os.environ else None
            if not has_set_value:
                has_set_value = (
                    f"{self.PROJECT_NAME_SAFE}_{name_to}"
                    if f"{self.PROJECT_NAME_SAFE}_{name_to}" in os.environ
                    else None
                )

            if has_set_value:
                continue

            parser, default_value = _VARIABLE_DEFINITIONS[name_to]
            ci_value = parser(name_from, None)
            if not ci_value:
                continue
            setattr(self, name_to, ci_value)

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


class AzurePipelinesMapper:
    MAPPING = {
        "BUILD_SOURCEBRANCHNAME": "GIT_COMMIT_REF_NAME",  # TODO: Do this programmatically instead
        "BUILD_SOURCEVERSION": "GIT_COMMIT_SHA",
        "SYSTEM_TEAMPROJECT": "PROJECT_NAME",
    }

    def __str__(self) -> str:
        return "Azure Pipelines"

    @property
    def is_active(self) -> bool:
        return bool(env.str("AZURE_HTTP_USER_AGENT", ""))

    @property
    def VALID_FILE_SECRET_PATH_PREFIXES(self) -> List[str]:
        return ["/builds/"]


class GitLabMapper:
    MAPPING = {
        "CI_COMMIT_REF_NAME": "GIT_COMMIT_REF_NAME",
        "CI_COMMIT_SHA": "GIT_COMMIT_SHA",
        "CI_DEFAULT_BRANCH": "GIT_DEFAULT_TARGET_BRANCH",
        "CI_ENVIRONMENT_SLUG": "ENVIRONMENT_SLUG",
        "CI_ENVIRONMENT_URL": "ENVIRONMENT_URL",
        "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "GIT_TARGET_BRANCH",
        "CI_PROJECT_DIR": "PROJECT_DIR",
        "CI_PROJECT_NAME": "PROJECT_NAME",
        "CI_PROJECT_PATH_SLUG": "PROJECT_PATH_SLUG",
        "CI_REGISTRY": "CONTAINER_REGISTRY",
        "CI_REGISTRY_IMAGE": "CONTAINER_REGISTRY_REPO",
        "CI_REGISTRY_PASSWORD": "CONTAINER_REGISTRY_PASSWORD",
        "CI_REGISTRY_USER": "CONTAINER_REGISTRY_USER",
        "KUBE_INGRESS_BASE_DOMAIN": "K8S_INGRESS_BASE_DOMAIN",
        "KUBE_INGRESS_PREVENT_ROBOTS": "K8S_INGRESS_PREVENT_ROBOTS",
        "KUBE_NAMESPACE": "K8S_NAMESPACE",
        "KUBE_CLUSTER_ISSUER": "K8S_CLUSTER_ISSUER",
        "KUBECONFIG": "KUBECONFIG",
    }

    def __str__(self) -> str:
        return "GitLab CI"

    @property
    def is_active(self) -> bool:
        return env.bool("GITLAB_CI", False)  # type: ignore

    @property
    def VALID_FILE_SECRET_PATH_PREFIXES(self) -> List[str]:
        return ["/builds/"]


settings = Settings()
