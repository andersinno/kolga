from hashlib import sha256
from typing import Any, Dict, List

from scripts.libs.docker import Docker
from scripts.utils.general import (
    env_var_safe_key,
    get_deploy_name,
    get_environment_vars_by_prefix,
    get_environment_vars_by_prefixes,
    get_secret_name,
)

from ..settings import settings

ICON = "📁"

PROJECT_ARG_SETTINGS_MAPPING = {
    "PROJECT_NAME": "name",
    "APP_INITIALIZE_COMMAND": "initialize_command",
    "APP_MIGRATE_COMMAND": "migrate_command",
    "ENVIRONMENT_URL": "url",
    "K8S_ADDITIONAL_HOSTNAMES": "additional_urls",
    "K8S_REQUEST_CPU": "request_cpu",
    "K8S_REQUEST_RAM": "request_ram",
    "SERVICE_PORT": "service_port",
}


class Project:
    name: str
    initialize_command: str
    migrate_command: str
    url: str
    additional_urls: List[str]
    request_cpu: str
    request_ram: str
    service_port: str

    dependency_projects: List["Project"]

    def __init__(
        self,
        track: str,
        secret_name: str = "",
        file_secret_name: str = "",
        basic_auth_secret_name: str = "",
        image: str = "",
        urls: str = "",
        is_dependent_project: bool = False,
        deploy_name: str = "",
        **kwargs: str,
    ) -> None:
        # Set variables from arguments and if they do not exist,
        # then default to settings variables.
        for env_var, attr in PROJECT_ARG_SETTINGS_MAPPING.items():
            if attr in kwargs:
                setattr(self, attr, kwargs[attr])
            else:
                setattr(self, attr, getattr(settings, env_var, ""))
        postfix = self.name

        self.track = track
        self.image = image
        self.secret_name = secret_name
        self.file_secret_name = file_secret_name
        self.basic_auth_secret_name = basic_auth_secret_name
        self.urls = urls
        self.is_dependent_project = is_dependent_project

        if not image:
            docker = Docker()
            self.image = docker.image_tag

        # TODO: Only set secret names if there are actual secrets
        if not self.secret_name:
            self.secret_name = get_secret_name(track=track, postfix=postfix)

        if not self.file_secret_name:
            file_secret_postfix = f"{postfix}-file"
            self.file_secret_name = get_secret_name(
                track=track, postfix=file_secret_postfix
            )

        self.deploy_name = deploy_name
        if not deploy_name:
            self.deploy_name = get_deploy_name(track=track, postfix=postfix)

        self.dependency_projects = (
            [] if is_dependent_project else self.get_dependency_projects(self.track)
        )

        secret_prefixes = (
            [f"{env_var_safe_key(self.name)}_{settings.K8S_SECRET_PREFIX}"]
            if self.is_dependent_project
            else [
                settings.K8S_SECRET_PREFIX,
                f"{env_var_safe_key(self.name)}_{settings.K8S_SECRET_PREFIX}",
            ]
        )
        self.secret_data = get_environment_vars_by_prefixes(prefixes=secret_prefixes)
        for dep_project in self.dependency_projects:
            self.secret_data[
                f"{env_var_safe_key(dep_project.name)}_URL"
            ] = dep_project.url

    def get_dependency_projects(self, track: str) -> List["Project"]:
        """
        Retrieves the dependecy projects defined by `depends_on_projects` env var

        Returns: A list of `ProjectModel`s
        """
        dependency_projects: List[Project] = []

        dependency_string = settings.DEPENDS_ON_PROJECTS
        if not dependency_string:
            return dependency_projects

        dependency_images = dependency_string.strip().split(" ")
        for image in dependency_images:
            # Ex. docker.example.com/project:23 -> docker.example.com/project -> project
            name = image.rsplit(":", 1)[0].split("/")[-1]
            # TODO: Add a unified way of settings the URL for both
            #       dependency and main project during the __init__ call.
            #       This could be achieved by passing the parent for instance
            #       and then calling a function that sets the URL during init.
            url = Project.get_dependency_project_url(name, self)

            project_env_vars = get_environment_vars_by_prefix(
                prefix=f"{env_var_safe_key(name)}_"
            )

            project_kwargs: Dict[str, Any] = {"additional_urls": []}
            for env_var in project_env_vars:
                project_arg = PROJECT_ARG_SETTINGS_MAPPING.get(env_var, None)
                if project_arg:
                    project_kwargs[project_arg] = project_env_vars[env_var]

            dependency_project = Project(
                name=name,
                image=image,
                is_dependent_project=True,
                track=track,
                url=url,
                **project_kwargs,
            )
            dependency_projects.append(dependency_project)

        return dependency_projects

    @staticmethod
    def get_dependency_project_url(project_name: str, parent_project: "Project") -> str:
        """
        Creates a project URL conforming to the RFC 1035

        The maximum length of a DNS label (for instance a subdomain) is 63.
        Therefor we need to make sure that we do not create subdomains longer
        than that, but still create subdomains that are close to subdomain
        to the original project for convenience.

        To achieve this, we hash the name of the dependency project and use
        the first 7 characters of the name (same as the short hash in Git).
        We then append this to the first 55 characters of the parent subdomain
        dividing the two with a hyphen/dash, resulting in a subdomain with max
        length 63.

        Args:
            project_name: Name of the dependency project
            parent_project: Parent project to the dependency prjoect

        Returns:
            A string with the URL to the dependency project
        """
        url_split = parent_project.url.split(".")
        if len(url_split) < 3 or url_split[0] == "www":
            raise ValueError(
                f"Can't set dependency URL for what looks like a production parent URL ({parent_project.url})"
            )

        project_hash = sha256(project_name.encode("utf-8")).hexdigest()

        parent_subdomain = url_split[0]
        dep_project_subdomain = f"{parent_subdomain[:55]}-{project_hash[:7]}"
        dep_project_url_split = [dep_project_subdomain] + url_split[1:]
        return ".".join(dep_project_url_split)

    @property
    def verbose_name(self) -> str:
        # Ex. my-test_project -> My test project
        return self.name.replace("-", "").replace("_", "").capitalize()
