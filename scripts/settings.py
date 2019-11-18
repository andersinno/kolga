import uuid
from typing import Any, List, Optional

import environs

env = environs.Env()
env.read_env()


class Settings:
    # PROJECT
    PROJECT_NAME: str = env.str("PROJECT_NAME", "")
    PROJECT_PATH_SLUG: str = env.str("PROJECT_PATH_SLUG", "")
    PROJECT_DIR: str = env.str("PROJECT_DIR", "")

    # DOCKER
    CONTAINER_REGISTRY_USER: str = env.str("CONTAINER_REGISTRY_USER", "")
    CONTAINER_REGISTRY_PASSWORD: str = env.str("CONTAINER_REGISTRY_PASSWORD", "")
    CONTAINER_REGISTRY: str = env.str("CONTAINER_REGISTRY", "docker.anders.fi")
    CONTAINER_REGISTRY_REPO: str = env.str("CONTAINER_REGISTRY_REPO", "")
    DOCKER_IMAGE_NAME: str = env.str("DOCKER_IMAGE_NAME", "")
    DOCKER_BUILD_SOURCE: str = env.str("DOCKER_BUILD_SOURCE", "Dockerfile")
    DOCKER_BUILD_CONTEXT: str = env.str("DOCKER_BUILD_CONTEXT", ".")
    DOCKER_HOST: str = env.str("DOCKER_HOST", "unix:///var/run/docker.sock")
    DOCKER_TEST_IMAGE_STAGE: str = env.str("DOCKER_TEST_IMAGE_STAGE", "development")

    # ENVIRONMENT
    ENVIRONMENT_SLUG: str = env.str("ENVIRONMENT_SLUG", "")
    ENVIRONMENT_URL: str = env.str("ENVIRONMENT_URL", "")
    SERVICE_PORT: str = env.str("SERVICE_PORT", "8000")

    # GIT
    GIT_COMMIT_SHA: str = env.str("GIT_COMMIT_SHA", "")
    GIT_COMMIT_REF_NAME: str = env.str("GIT_COMMIT_REF_NAME", "")

    # APPLICATION
    DATABASE_USER: str = env.str("DATABASE_USER", "user")
    DATABASE_PASSWORD: str = env.str("DATABASE_PASSWORD", str(uuid.uuid4()))
    DATABASE_DB: str = env.str("DATABASE_DB", "appdb")
    POSTGRES_VERSION_TAG: str = env.str("POSTGRES_VERSION_TAG", "9.6")
    MYSQL_VERSION_TAG: str = env.str("MYSQL_VERSION_TAG", "5.7")
    MYSQL_ENABLED: bool = env.bool("MYSQL_ENABLED", False)
    POSTGRES_ENABLED: bool = env.bool("POSTGRES_ENABLED", True)
    APP_INITIALIZE_COMMAND: str = env.str("APP_INITIALIZE_COMMAND", "")
    APP_MIGRATE_COMMAND: str = env.str("APP_MIGRATE_COMMAND", "")

    # KUBERNETES
    # Note: Either separate k8s config vars or KUBECONFIG needs to be present
    K8S_API_KEY: str = env.str("K8S_API_KEY", "")
    K8S_API_CA_PEM_FILE: str = env.str("K8S_API_CA_PEM_FILE", "")
    K8S_API_URL: str = env.str("K8S_API_URL", "")
    K8S_INGRESS_BASE_DOMAIN: str = env.str("K8S_INGRESS_BASE_DOMAIN", "")
    K8S_SECRET_PREFIX: str = env.str("K8S_SECRET_PREFIX", "K8S_SECRET_")
    K8S_NAMESPACE: str = env.str("K8S_NAMESPACE", "")
    KUBECONFIG: str = env.str("KUBECONFIG", "")

    def __init__(self) -> None:
        self.active_ci: Optional[Any] = None
        self.supported_cis: List[Any] = [GitLabMapper()]

        self._get_ci_environment()
        if self.active_ci:
            self._map_ci_variables()

    def _get_ci_environment(self) -> None:
        for ci in self.supported_cis:
            if ci.is_active:
                self.active_ci = ci
                break

    def _map_ci_variables(self) -> None:
        if not self.active_ci:
            return None
        for name_from, name_to in self.active_ci.MAPPING.items():
            env_value = env.str(name_from, "")
            setattr(self, name_to, env_value)


class GitLabMapper:
    MAPPING = {
        "CI_PROJECT_NAME": "PROJECT_NAME",
        "CI_REGISTRY_USER": "CONTAINER_REGISTRY_USER",
        "CI_REGISTRY_PASSWORD": "CONTAINER_REGISTRY_PASSWORD",
        "CI_REGISTRY": "CONTAINER_REGISTRY",
        "CI_REGISTRY_IMAGE": "CONTAINER_REGISTRY_REPO",
        "CI_ENVIRONMENT_SLUG": "ENVIRONMENT_SLUG",
        "CI_ENVIRONMENT_URL": "ENVIRONMENT_URL",
        "CI_PROJECT_PATH_SLUG": "PROJECT_PATH_SLUG",
        "CI_COMMIT_SHA": "GIT_COMMIT_SHA",
        "CI_COMMIT_REF_NAME": "GIT_COMMIT_REF_NAME",
        "KUBE_URL": "K8S_API_URL",
        "KUBE_TOKEN": "K8S_API_KEY",
        "KUBE_CA_PEM_FILE": "K8S_API_CA_PEM_FILE",
        "KUBE_NAMESPACE": "K8S_NAMESPACE",
        "KUBE_INGRESS_BASE_DOMAIN": "K8S_INGRESS_BASE_DOMAIN",
        "KUBECONFIG": "KUBECONFIG",
        "CI_PROJECT_DIR": "PROJECT_DIR",
    }

    def __str__(self) -> str:
        return "GitLab CI"

    @property
    def is_active(self) -> bool:
        return env.bool("GITLAB_CI", False)  # type: ignore


settings = Settings()
