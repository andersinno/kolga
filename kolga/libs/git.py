import os

from kolga.settings import settings
from kolga.utils.general import run_os_command
from kolga.utils.logger import logger


class Git:
    """
    A wrapper class around various Git tools
    """

    ICON = "🐙"

    def __init__(self) -> None:
        # We declare the current working dir as a safe directory in git configuration.
        # This is because since the CVE-2022-24765 vulnerability, Git does not trust
        # directories that are owned by other users than the current user. In some
        # environments, like Github Actions, the mounted source directory is owned by
        # another user and therefore this is required.
        config_command = [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            os.getcwd(),
        ]
        result = run_os_command(config_command)
        if result.return_code:
            logger.std(result, raise_exception=True)

    def update_submodules(self, depth: int = 0, jobs: int = 0) -> None:
        """
        Update all submodules

        Returns:
            None
        """
        os_command = [
            "git",
            "submodule",
            "update",
            "--init",
            "--recursive",
        ]

        if depth:
            os_command += ["--depth", f"{depth}"]

        if jobs:
            os_command += ["--jobs", f"{jobs}"]

        logger.info(icon=f"{self.ICON} 🌱", title="Updating submodules: ", end="")

        with settings.plugin_manager.lifecycle.git_submodule_update():
            result = run_os_command(os_command)
            if result.return_code:
                logger.std(result, raise_exception=True)
            logger.success()
