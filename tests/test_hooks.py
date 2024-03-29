import inspect
from collections import OrderedDict
from typing import Any, List, Optional, Tuple, Type, cast
from unittest import mock

import pytest
from environs import Env

from kolga.hooks import hookimpl
from kolga.libs.docker import Docker
from kolga.libs.git import Git
from kolga.libs.kubernetes import Kubernetes
from kolga.libs.project import Project
from kolga.plugins.base import PluginBase
from kolga.settings import settings
from tests.testcase import load_plugin


class _TestPlugin(PluginBase):
    name = "test_plugin"
    verbose_name = "Kolga Example Plugin"
    version = 0.1

    def __init__(self, env: Env) -> None:
        self.configure(env)

    @hookimpl
    def project_deployment_complete(self, project: Project) -> Optional[bool]:
        if not self.configured:
            return None

        return True


@load_plugin(_TestPlugin)
def test_create_deployment() -> None:
    results: Any = settings.plugin_manager.hook.project_deployment_begin(
        project=Project(track="testing", url="test.example.com"),
        track="testing",
        namespace="testing",
    )
    results = cast(List[Optional[bool]], results)
    assert len(results) == 0

    results: Any = settings.plugin_manager.hook.project_deployment_complete(  # type: ignore[no-redef]
        exception=None,
        namespace="testing",
        project=Project(track="testing", url="test.example.com"),
        track="testing",
    )
    results = cast(List[Optional[bool]], results)
    assert len(results) and all(results)


def call_tracking_plugin_factory() -> Tuple[Type[PluginBase], OrderedDict[str, bool]]:
    hook_calls: OrderedDict[str, bool] = OrderedDict()

    def append_hook_call(retval: bool = True) -> bool:
        # Get function name from callers stack frame
        hook_name = inspect.currentframe().f_back.f_code.co_name  # type: ignore[union-attr]
        hook_calls[hook_name] = retval
        return retval

    class CallTrackingPlugin(PluginBase):
        name = "call_tracking_plugin"
        verbose_name = "Call-tracking Test plugin"
        version = 0.1

        @hookimpl
        def container_build_begin(self) -> Optional[bool]:
            return append_hook_call()

        @hookimpl
        def container_build_complete(
            self, exception: Optional[Exception]
        ) -> Optional[bool]:
            return append_hook_call(exception is None)

        @hookimpl
        def container_build_stage_begin(self) -> Optional[bool]:
            return append_hook_call()

        @hookimpl
        def container_build_stage_complete(
            self, exception: Optional[Exception]
        ) -> Optional[bool]:
            return append_hook_call(exception is None)

        @hookimpl
        def git_submodule_update_begin(self) -> Optional[bool]:
            return append_hook_call()

        @hookimpl
        def git_submodule_update_complete(
            self, exception: Optional[Exception]
        ) -> Optional[bool]:
            return append_hook_call(exception is None)

        @hookimpl
        def project_deployment_begin(self) -> Optional[bool]:
            return append_hook_call()

        @hookimpl
        def project_deployment_complete(
            self, exception: Optional[Exception]
        ) -> Optional[bool]:
            return append_hook_call(exception is None)

        @hookimpl
        def service_deployment_begin(self) -> Optional[bool]:
            return append_hook_call()

        @hookimpl
        def service_deployment_complete(
            self, exception: Optional[Exception]
        ) -> Optional[bool]:
            return append_hook_call(exception is None)

    return CallTrackingPlugin, hook_calls


def test_lifecycle_hook_calls() -> None:
    image = mock.MagicMock()
    ns = track = "testing"
    project = mock.MagicMock()
    service = mock.MagicMock()
    stage = mock.MagicMock()

    Plugin, hook_calls = call_tracking_plugin_factory()
    with load_plugin(Plugin):
        # Container build hooks
        settings.plugin_manager.hook.container_build_begin()
        settings.plugin_manager.hook.container_build_complete(exception=None)
        settings.plugin_manager.hook.container_build_stage_begin(
            image=image, stage=stage
        )
        settings.plugin_manager.hook.container_build_stage_complete(
            exception=None, image=image, stage=stage
        )

        # Git submodule hooks
        settings.plugin_manager.hook.git_submodule_update_begin()
        settings.plugin_manager.hook.git_submodule_update_complete(exception=None)

        # Application deployment hooks
        settings.plugin_manager.hook.project_deployment_begin(
            namespace=ns, project=project, track=track
        )

        settings.plugin_manager.hook.project_deployment_complete(
            exception=None, namespace=ns, project=project, track=track
        )

        # Service deployment hooks
        settings.plugin_manager.hook.service_deployment_begin(
            namespace=ns, service=service, track=track
        )
        settings.plugin_manager.hook.service_deployment_complete(
            exception=None, namespace=ns, service=service, track=track
        )

    assert [*hook_calls.keys()] == [
        "container_build_begin",
        "container_build_complete",
        "container_build_stage_begin",
        "container_build_stage_complete",
        "git_submodule_update_begin",
        "git_submodule_update_complete",
        "project_deployment_begin",
        "project_deployment_complete",
        "service_deployment_begin",
        "service_deployment_complete",
    ]


@mock.patch("kolga.libs.docker.run_os_command", **{"return_value.return_code": 0})  # type: ignore
def test_lifecycle_hooks_build(_: mock.MagicMock) -> None:
    d = Docker()

    Plugin, hook_calls = call_tracking_plugin_factory()
    with load_plugin(Plugin):
        d.build_stages()

    assert [*hook_calls.keys()] == [
        "container_build_begin",
        "container_build_stage_begin",
        "container_build_stage_complete",
        "container_build_complete",
    ]


@mock.patch("kolga.libs.git.run_os_command", **{"return_value.return_code": 0})  # type: ignore
def test_lifecycle_hooks_git_submodule_update(_: mock.MagicMock) -> None:
    g = Git()

    Plugin, hook_calls = call_tracking_plugin_factory()
    with load_plugin(Plugin):
        g.update_submodules()

    assert [*hook_calls.keys()] == [
        "git_submodule_update_begin",
        "git_submodule_update_complete",
    ]


@mock.patch("kolga.libs.kubernetes.Kubernetes.create_client")
def test_lifecycle_hooks_deployment(_: mock.MagicMock) -> None:
    ns = track = "testing"
    project = Project(track=track, url="example.com")
    service = mock.MagicMock()

    k = Kubernetes(track=track)
    k.helm = mock.MagicMock(**{"upgrade_chart.return_value.return_code": 0})
    mock.patch("kolga.libs.kubernetes.KubeLoggerThread")

    Plugin, hook_calls = call_tracking_plugin_factory()
    with load_plugin(Plugin):
        k.deploy_service(namespace=ns, service=service, track=track)
        k.create_application_deployment(namespace=ns, project=project, track=track)

    assert [*hook_calls.keys()] == [
        "service_deployment_begin",
        "service_deployment_complete",
        "project_deployment_begin",
        "project_deployment_complete",
    ]


def test_lifecycle_failure() -> None:
    g = Git()

    with mock.patch(
        "kolga.libs.git.run_os_command",
        mock.MagicMock(side_effect=RuntimeError()),
    ):
        Plugin, hook_calls = call_tracking_plugin_factory()
        with load_plugin(Plugin):
            with pytest.raises(RuntimeError):
                g.update_submodules()

    assert hook_calls["git_submodule_update_begin"] is True
    assert hook_calls["git_submodule_update_complete"] is False
