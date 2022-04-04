from typing import List

from environs import Env

from kolga.hooks import hookimpl
from kolga.plugins.base import PluginBase
from kolga.plugins.exceptions import PluginMissingConfiguration
from kolga.utils.general import run_os_command
from kolga.utils.logger import logger


class KolgaBinfmtPlugin(PluginBase):
    name = "binfmt"
    verbose_name = "Binfmt plugin for Kolga"
    version = 0.1

    # Environment variables
    BINFMT_ENABLED: bool
    DOCKER_BUILD_PLATFORMS: List[str]

    def __init__(self, env: Env) -> None:
        self.required_variables = [
            ("BINFMT_ENABLED", env.bool),
            ("DOCKER_BUILD_PLATFORMS", env.list),
        ]
        self.configure(env)

        if not self.BINFMT_ENABLED or not self.DOCKER_BUILD_PLATFORMS:
            raise PluginMissingConfiguration("Binfmt not enabled")

    def install_binfmt_platforms(self) -> None:
        platforms = ",".join(self.DOCKER_BUILD_PLATFORMS)
        logger.info(
            icon="🐳 ℹ️", message=f"Installing platform support for: {platforms}"
        )
        binfmt_install_command = [
            "docker",
            "run",
            "--privileged",
            "--rm",
            "tonistiigi/binfmt",
            "--install",
            platforms,
        ]

        result = run_os_command(binfmt_install_command)
        if result.return_code:
            logger.std(result, raise_exception=True)

    @hookimpl
    def buildx_setup_buildkit_begin(self) -> None:
        self.install_binfmt_platforms()
