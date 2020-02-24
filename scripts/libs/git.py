from scripts.utils.general import run_os_command
from scripts.utils.logger import logger


class Git:
    """
    A wrapper class around various Git tools
    """

    ICON = "🐙"

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

        result = run_os_command(os_command)
        if result.return_code:
            logger.std(result, raise_exception=True)
        logger.success()
