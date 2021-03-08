import json
import os
import sys
import tempfile
import uuid
from itertools import chain
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    ItemsView,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import pluggy  # type: ignore
from dotenv import dotenv_values
from environs import Env
from pydantic import BaseConfig, BaseSettings, Extra, Field

from kolga.hooks.exceptions import PluginMissingConfiguration
from kolga.hooks.hookspec import KolgaHookSpec
from kolga.hooks.plugins import PluginBase
from kolga.plugins import KOLGA_CORE_PLUGINS
from kolga.utils.exceptions import ImproperlyConfigured, NoClusterConfigError
from kolga.utils.fields import (
    BasicAuthUserList,
    split_comma_separated_values,
    unescape_string_values,
)
from kolga.utils.general import deep_get, env_var_safe_key, kubernetes_safe_name
from kolga.utils.logger import logger

if TYPE_CHECKING:
    from pydantic.env_settings import SettingsSourceCallable
    from pydantic.fields import ModelField


env = Env()


def settings_sources(
    init_settings: "SettingsSourceCallable",
    env_settings: "SettingsSourceCallable",
    file_secret_settings: "SettingsSourceCallable",
) -> Tuple["SettingsSourceCallable", ...]:
    return init_settings, env_settings, source_env_files, source_ci_mapper


def source_ci_mapper(settings: BaseSettings) -> Dict[str, Any]:
    Mapper = BaseCI.get_active_mapper_cls()
    if not Mapper:
        return {}
    return Mapper().map_variables(settings.__fields__)


def source_env_files(settings: BaseSettings) -> Dict[str, str]:
    def env_files() -> Generator[Path, None, None]:
        if build_artifacts := env.path("BUILD_ARTIFACT_FOLDER", None):
            yield from build_artifacts.glob("*.env")

        if service_artifacts := env.path("SERVICE_ARTIFACT_FOLDER", None):
            yield from service_artifacts.glob("*.env")

    def load_env_files() -> Generator[Dict[str, str], None, None]:
        for env_file in env_files():
            d = dotenv_values(env_file, interpolate=False)
            yield {k: v for k, v in d.items() if v is not None}

    # Merge dicts
    dict_items = cast(Callable[[Dict[str, str]], ItemsView[str, str]], dict.items)
    return dict(chain.from_iterable(map(dict_items, load_env_files())))


class ProjectNameSetting(BaseSettings):
    """
    Settings class used to get the project name.

    This is done as a separate setting since the value needs to be known before
    the ``Settings`` class can be initialized. The same sources (environment
    variables, build & services artifacts, and CI mappers) are used as for the
    ``Settings`` class.
    """

    PROJECT_NAME: Optional[str]

    class Config(BaseConfig):
        case_sensitive = True
        customise_sources = settings_sources
        env_file_encoding = "utf-8"
        extra = Extra.ignore


class SettingsValues(BaseSettings):
    APP_INITIALIZE_COMMAND: str = ""
    APP_MIGRATE_COMMAND: str = ""
    BUILD_ARTIFACT_FOLDER: str = ""
    BUILDKIT_CACHE_DISABLE: bool = False
    BUILDKIT_CACHE_IMAGE_NAME: str = "cache"
    BUILDKIT_CACHE_REPO: str = ""
    BUILT_DOCKER_TEST_IMAGE: str = ""
    CONTAINER_REGISTRY: str = ""
    CONTAINER_REGISTRY_PASSWORD: str = ""
    CONTAINER_REGISTRY_REPO: str = ""
    CONTAINER_REGISTRY_USER: str = ""
    DATABASE_DB: str = "appdb"
    DATABASE_PASSWORD: str = Field(default_factory=lambda: f"{uuid.uuid4()}")
    DATABASE_USER: str = "user"
    DEFAULT_TRACK: str = "stable"
    DEPENDS_ON_PROJECTS: str = ""
    DOCKER_BUILD_ARG_PREFIX: str = "DOCKER_BUILD_ARG_"
    DOCKER_BUILD_CONTEXT: str = "."
    DOCKER_BUILD_SOURCE: str = "Dockerfile"
    DOCKER_HOST: str = ""
    DOCKER_IMAGE_NAME: str = ""
    DOCKER_IMAGE_TAGS: Optional[List[str]] = None
    DOCKER_TEST_IMAGE_STAGE: str = "development"
    ENVIRONMENT_SLUG: str = ""
    ENVIRONMENT_URL: str = ""
    GIT_COMMIT_REF_NAME: str = ""
    GIT_COMMIT_SHA: str = ""
    GIT_DEFAULT_TARGET_BRANCH: str = "master"
    GIT_TARGET_BRANCH: str = ""
    JOB_ACTOR: str = ""
    K8S_ADDITIONAL_HOSTNAMES: List[str] = []
    K8S_CERTMANAGER_USE_OLD_API: bool = False
    K8S_CLUSTER_ISSUER: str = ""
    K8S_FILE_SECRET_MOUNTPATH: str = "/tmp/secrets"  # nosec
    K8S_FILE_SECRET_PREFIX: str = "K8S_FILE_SECRET_"
    K8S_HPA_ENABLED: bool = False
    K8S_HPA_MAX_CPU_AVG: int = 75
    K8S_HPA_MAX_RAM_AVG: int = 0
    K8S_HPA_MAX_REPLICAS: int = 3
    K8S_HPA_MIN_REPLICAS: int = 1
    K8S_INGRESS_ANNOTATIONS: List[str] = []
    K8S_INGRESS_BASE_DOMAIN: str = ""
    K8S_INGRESS_BASIC_AUTH: BasicAuthUserList = Field([])
    K8S_INGRESS_DISABLED: bool = False
    K8S_INGRESS_MAX_BODY_SIZE: str = "100m"
    K8S_INGRESS_PREVENT_ROBOTS: bool = False
    K8S_INGRESS_SECRET_NAME: str = ""
    K8S_INGRESS_WHITELIST_IPS: str = ""
    K8S_LIMIT_CPU: str = ""
    K8S_LIMIT_RAM: str = ""
    K8S_LIVENESS_FILE: str = ""
    K8S_LIVENESS_PATH: str = "/healthz"
    K8S_NAMESPACE: str = ""
    K8S_PERSISTENT_STORAGE_ACCESS_MODE: str = "ReadWriteOnce"
    K8S_PERSISTENT_STORAGE: bool = False
    K8S_PERSISTENT_STORAGE_PATH: str = ""
    K8S_PERSISTENT_STORAGE_SIZE: str = "1Gi"
    K8S_PERSISTENT_STORAGE_STORAGE_TYPE: str = "standard"
    K8S_PROBE_FAILURE_THRESHOLD: int = 3
    K8S_PROBE_INITIAL_DELAY: int = 60
    K8S_PROBE_PERIOD: int = 10
    K8S_READINESS_FILE: str = ""
    K8S_READINESS_PATH: str = "/readiness"
    K8S_REPLICACOUNT: int = 1
    K8S_REQUEST_CPU: str = "50m"
    K8S_REQUEST_RAM: str = "128Mi"
    K8S_SECRET_PREFIX: str = "K8S_SECRET_"
    K8S_TEMP_STORAGE_PATH: str = ""
    KOLGA_DEBUG: bool = False
    KOLGA_JOBS_ONLY: bool = False
    KUBECONFIG: str = ""
    MYSQL_VERSION_TAG: str = "5.7"
    POSTGRES_IMAGE: str = "docker.io/bitnami/postgresql:9.6"
    PR_ASSIGNEES: str = ""
    PR_ID: str = ""
    PR_TITLE: str = ""
    PR_URL: str = ""
    PROJECT_DIR: str = ""
    PROJECT_ID: str = ""
    PROJECT_NAME: str = ""
    PROJECT_PATH_SLUG: str = ""
    RABBITMQ_VERSION_TAG: str = "3.8.5"
    SERVICE_ARTIFACT_FOLDER: str = ""
    SERVICE_PORT: int = 8000
    TRACK: str = ""
    VAULT_ADDR: str = ""
    VAULT_JWT_AUTH_PATH: str = "jwt"
    VAULT_JWT_PRIVATE_KEY: str = ""
    VAULT_JWT: str = ""
    VAULT_KV_SECRET_MOUNT_POINT: str = "secrets"
    VAULT_KV_VERSION: int = 2
    VAULT_TF_SECRETS: bool = False
    VAULT_TLS_ENABLED: bool = True


class Settings(SettingsValues):
    _active_ci: Optional["BaseCI"]
    _devops_root_path: Path
    _plugin_manager: pluggy.PluginManager

    @property
    def active_ci(self) -> Optional["BaseCI"]:
        if not hasattr(self, "_active_ci"):
            Mapper = BaseCI.get_active_mapper_cls()
            if Mapper:
                self._active_ci = Mapper()
            else:
                self._active_ci = None
        return self._active_ci

    @property
    def devops_root_path(self) -> Path:
        if not hasattr(self, "_devops_root_path"):
            self._devops_root_path = Path(sys.argv[0]).resolve().parent
        return self._devops_root_path

    @property
    def plugin_manager(self) -> pluggy.PluginManager:
        if not hasattr(self, "_plugin_manager"):
            self._plugin_manager = self._setup_pluggy()
        return self._plugin_manager

    # TODO: For some reason mypy complains about __init__ being already defined
    #       on the line where this class starts. Ignoring it for now.
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        # TODO: Could this be done in ``Config.prepare_field()``?
        project_name_prefix = env_var_safe_key(self.get_project_name())
        for field in self.__fields__.values():
            key = field.name
            field.field_info.extra["env_names"] = (key, f"{project_name_prefix}_{key}")

        if self.active_ci:
            config = cast("Settings.Config", self.__config__)
            config.unescape_strings = self.active_ci.UNESCAPE_ENVIRONMENT_VARIABLES

        super().__init__(*args, **kwargs)

        self._plugin_manager = self._setup_pluggy()

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

    def _load_plugin(self, plugin: Type[PluginBase]) -> Tuple[bool, str]:
        try:
            self.plugin_manager.register(plugin(env), name=plugin.name)
        except PluginMissingConfiguration as e:
            return False, f"⚠️  {e}"
        return True, "✅"

    def _unload_plugin(self, plugin: Union[PluginBase, Type[PluginBase]]) -> Any:
        # We need to first fetch the instance of the plugin in order to unregister it.
        # If we do not do this, Pluggy will not properly unregister as it will try
        # to do it on the class and not the instance, which will not hard-fail, but
        # will only partially unregister the plugin, leaving it still to be called
        # by hooks.
        _to_be_unregistered_plugin = self.plugin_manager.get_plugin(plugin.name)

        return self.plugin_manager.unregister(_to_be_unregistered_plugin)

    def get_project_name(self) -> str:
        project_name = ProjectNameSetting().PROJECT_NAME
        if not project_name:
            raise AssertionError("No project name could be found!")

        return project_name

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

            logger.info(message=f"Created a kubeconfig file using {key}")

            break

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

    class Config(BaseConfig):
        case_sensitive = True
        customise_sources = settings_sources
        extra = Extra.ignore
        json_loads = lambda x: x  # Disable JSON parsing.  # noqa: E731
        unescape_strings = False
        underscore_attrs_are_private = True

        @classmethod
        def prepare_field(cls, field: "ModelField") -> None:
            validators = field.pre_validators or ()

            # Unescape strings
            if field.type_ is str:
                validators = field.pre_validators = [
                    unescape_string_values,
                    *validators,
                ]

            # Split comma separated lists
            if field.is_complex() and field.outer_type_ is List[str]:
                field.pre_validators = [split_comma_separated_values, *validators]


class BaseCI:
    MAPPERS: List[Type["BaseCI"]] = []
    MAPPING: Dict[str, str] = {}
    UNESCAPE_ENVIRONMENT_VARIABLES = False

    @property
    def VALID_FILE_SECRET_PATH_PREFIXES(self) -> List[str]:
        return []

    def map_variables(self, fields: Dict[str, "ModelField"]) -> Dict[str, Any]:
        """
        Map CI variables to settings

        If the source name starts with '=', get the value from mapper's
        attribute. Otwerwise read the value from environment.
        """
        values = {}

        for name_to, name_from in self.MAPPING.items():
            if name_to not in fields:
                logger.warning(
                    message=f"CI variable mapping failed, no setting called {name_to}"
                )
                continue

            if name_from.startswith("="):
                name_from = name_from[1:]
                try:
                    value = getattr(self, name_from)
                except AttributeError:
                    logger.warning(
                        message=f"CI variable mapping failed, no mapper attribute called {name_from}"
                    )
                    continue
            elif name_from in os.environ:
                raw_value = os.environ.get(name_from)
                value, error = fields[name_to].validate(raw_value, {}, loc=name_from)
                if error:
                    raise ImproperlyConfigured(
                        f"Invalid valid value: {name_from}={raw_value}"
                    )
            else:
                value = None

            if value is not None:
                values[name_to] = value

        return values

    @classmethod
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.MAPPERS.append(cls)

    @classmethod
    def get_active_mapper_cls(cls) -> Optional[Type["BaseCI"]]:
        for Mapper in cls.MAPPERS:
            if Mapper.is_active():
                return Mapper
        return None

    @classmethod
    def is_active(cls) -> bool:
        return False


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
    def VALID_FILE_SECRET_PATH_PREFIXES(self) -> List[str]:
        return ["/builds/"]

    @classmethod
    def is_active(cls) -> bool:
        return bool(env.str("AZURE_HTTP_USER_AGENT", ""))


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

    @classmethod
    def is_active(cls) -> bool:
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
    UNESCAPE_ENVIRONMENT_VARIABLES = True
    _EVENT_DATA: Optional[Dict[str, Any]]

    def __init__(self) -> None:
        self._set_event_data_variables()

    def __str__(self) -> str:
        return "GitHub Actions"

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

    @classmethod
    def is_active(cls) -> bool:
        return env.bool("GITHUB_ACTIONS", False)  # type: ignore


settings = Settings()
