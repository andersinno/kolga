from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar, cast

import pluggy

F = TypeVar("F", bound=Callable[..., Any])
hookspec = cast(Callable[[F], F], pluggy.HookspecMarker("kolga"))

if TYPE_CHECKING:
    from kolga.libs.project import Project


class KolgaHookSpec:
    """
    Kolga Hook Specification
    """

    @hookspec
    def project_deployment_complete(
        self, project: "Project", track: str, namespace: str
    ) -> Optional[bool]:
        """
        Fired when a new deployment of a project has completed successfully.

        Args:
            namespace: Namespace of the deployment
            track: Track of the deployment
            project: A `Project` object including all information about the project

        Returns:
            Optionally returns a boolean value denoting if the plugin
            finished successfully.

            The return value is not acted upon by Kólga.
        """
