from typing import Optional

from environs import Env

from kolga.hooks import hookimpl
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
    results = settings.plugin_manager.hook.project_deployment_complete(
        project=Project(track="testing", url="test.example.com"),
        track="testing",
        namespace="testing",
    )

    assert len(results) and results[0] is True
