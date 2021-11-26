from contextlib import AbstractContextManager, contextmanager
from typing import TYPE_CHECKING, Any, Callable, Generator, Optional, TypeVar, cast

import pluggy

F = TypeVar("F", bound=Callable[..., Any])
hookspec = cast(Callable[[F], F], pluggy.HookspecMarker("kolga"))

if TYPE_CHECKING:
    from pluggy import PluginManager

    from kolga.libs.project import Project
    from kolga.libs.service import Service
    from kolga.utils.models import DockerImage


class KolgaHookSpec:
    """
    Kolga Hook Specification
    """

    @hookspec
    def application_shutdown(self, exception: Optional[Exception]) -> Optional[bool]:
        """
        Fired when the application is exiting.

        Args:
            exception: An ``Exception`` object if one is raised during the lifecycle.


        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """

    @hookspec
    def application_startup(self) -> Optional[bool]:
        """
        Fired when the application is starting.

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
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


def _make_manager(
    at_enter: Callable[..., Any],
    at_exit: Callable[..., Any],
) -> Callable[..., AbstractContextManager[Any]]:
    @contextmanager
    def inner(*args: Any, **kwargs: Any) -> Generator[None, None, None]:
        at_enter(*args, **kwargs)
        try:
            yield
        except Exception as exc:
            at_exit(*args, **{**kwargs, "exception": exc})
            raise
        else:
            at_exit(*args, **{"exception": None, **kwargs})

    return inner


class LifeCycleManager:
    def __init__(self, pm: "PluginManager[KolgaHookSpec]") -> None:
        self.application = _make_manager(
            pm.hook.application_startup,
            pm.hook.application_shutdown,
        )
        self.container_build = _make_manager(
            pm.hook.container_build_begin,
            pm.hook.container_build_complete,
        )
        self.container_build_stage = _make_manager(
            pm.hook.container_build_stage_begin,
            pm.hook.container_build_stage_complete,
        )
        self.git_submodule_update = _make_manager(
            pm.hook.git_submodule_update_begin,
            pm.hook.git_submodule_update_complete,
        )
        self.project_deployment = _make_manager(
            pm.hook.project_deployment_begin,
            pm.hook.project_deployment_complete,
        )
        self.service_deployment = _make_manager(
            pm.hook.service_deployment_begin,
            pm.hook.service_deployment_complete,
        )
