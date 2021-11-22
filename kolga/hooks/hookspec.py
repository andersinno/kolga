from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar, cast

import pluggy

F = TypeVar("F", bound=Callable[..., Any])
hookspec = cast(Callable[[F], F], pluggy.HookspecMarker("kolga"))

if TYPE_CHECKING:
    from kolga.libs.project import Project
    from kolga.libs.service import Service
    from kolga.utils.models import DockerImage


class KolgaHookSpec:
    """
    Kolga Hook Specification
    """

    @hookspec
    def container_build_begin(self) -> Optional[bool]:
        """
        Fired when building of containers is starting.

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def container_build_complete(
        self,
        exception: Optional[Exception],
    ) -> Optional[bool]:
        """
        Fired when containers are built successfully.

        Args:
            exception: An ``Exception`` object if one is raised during the lifecycle.

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def container_build_stage_begin(
        self,
        image: "DockerImage",
        stage: str,
    ) -> Optional[bool]:
        """
        Fired when building of container stage is starting.

        Args:
            image: An ``DockerImage`` object
            stage: Stage name

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def container_build_stage_complete(
        self,
        exception: Optional[Exception],
        image: "DockerImage",
        stage: str,
    ) -> Optional[bool]:
        """
        Fired when container stage is built successfully.

        Args:
            exception: An ``Exception`` object if one is raised during the lifecycle.
            image: An ``DockerImage`` object
            stage: Stage name

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def git_submodule_update_begin(self) -> Optional[bool]:
        """
        Fired when ``git submodule update`` is staring.

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def git_submodule_update_complete(
        self,
        exception: Optional[Exception],
    ) -> Optional[bool]:
        """
        Fired when ``git submodule update`` is completed successfully.

        Args:
            exception: An ``Exception`` object if one is raised during the lifecycle.

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def project_deployment_begin(
        self,
        namespace: str,
        project: "Project",
        track: str,
    ) -> Optional[bool]:
        """
        Fired when a new deployment of a project is starting.

        Args:
            namespace: Namespace of the deployment
            project: A ``Project`` object including all information about the project
            track: Track of the deployment

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def project_deployment_complete(
        self,
        exception: Optional[Exception],
        namespace: str,
        project: "Project",
        track: str,
    ) -> Optional[bool]:
        """
        Fired when a new deployment of a project has completed successfully.

        Args:
            exception: An ``Exception`` object if one is raised during the lifecycle.
            namespace: Namespace of the deployment
            project: A ``Project`` object including all information about the project
            track: Track of the deployment

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def service_deployment_begin(
        self,
        namespace: str,
        service: "Service",
        track: str,
    ) -> Optional[bool]:
        """
        Fired when a new deployment of a service is starting.

        Args:
            namespace: Namespace of the deployment
            service: A ``Service`` object including all information about the service
            track: Track of the deployment

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def service_deployment_complete(
        self,
        exception: Optional[Exception],
        namespace: str,
        service: "Service",
        track: str,
    ) -> Optional[bool]:
        """
        Fired when a new deployment of a service has completed successfully.

        Args:
            exception: An ``Exception`` object if one is raised during the lifecycle.
            namespace: Namespace of the deployment
            service: A ``Service`` object including all information about the service
            track: Track of the deployment

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """
