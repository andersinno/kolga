from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from scripts.utils.logger import logger
from scripts.utils.models import SubprocessResult

from ..utils.general import run_os_command


class Helm:
    """
    A wrapper class around various Helm tools
    """

    ICON = "⎈"

    def setup_helm(self) -> None:
        """
        Makes sure that Helm is ready to use

        Returns:
            None
        """
        logger.info(icon=f"{self.ICON}  🚀", title="Initializing Helm")

        # TODO: Remove once this is added by default and Helm 3 is stable
        self.add_repo("stable", "https://kubernetes-charts.storage.googleapis.com/")

        self.update_repos()

    def add_repo(self, repo_name: str, repo_url: str, update: bool = True) -> None:
        logger.info(
            icon=f"{self.ICON}  ➕",
            title=f"Adding Helm repo {repo_url} with name {repo_name}: ",
            end="",
        )
        result = run_os_command(["helm", "repo", "add", repo_name, repo_url])
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=True)

        if update:
            self.update_repos()

    def remove_repo(self, repo_name: str) -> None:
        logger.info(
            icon=f"{self.ICON}  ➖", title=f"Removing Helm repo {repo_name}: ", end="",
        )
        result = run_os_command(["helm", "repo", "remove", repo_name])
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=True)

    def update_repos(self) -> None:
        logger.info(icon=f"{self.ICON}  🔄", title="Updating Helm repos: ", end="")
        result = run_os_command(["helm", "repo", "update"])
        if not result.return_code:
            logger.success()
        else:
            logger.std(result, raise_exception=True)

    @staticmethod
    def get_chart_name(chart: str) -> str:
        chart_name = chart.split("/")[-1:]
        if not chart_name or not chart_name[0]:
            logger.error(
                message=f"No chart name found in {chart}",
                error=ValueError(),
                raise_exception=True,
            )
        return chart_name[0]

    def upgrade_chart(
        self,
        name: str,
        values: Dict[str, Any],
        namespace: str,
        chart: str = "",
        chart_path: Optional[Path] = None,
        install: bool = True,
        version: Optional[str] = None,
        raise_exception: bool = True,
    ) -> SubprocessResult:
        if chart_path and not chart_path.exists():
            logger.error(
                message=f"Path '{str(chart_path)}' does not exist",
                error=OSError(),
                raise_exception=True,
            )
        elif chart_path:
            chart = str(chart_path)

        logger.info(
            icon=f"{self.ICON}  📄", title=f"Upgrading chart from '{chart}': ", end="",
        )

        # Construct initial helm upgrade command
        install_arg = "--install" if install else ""
        helm_command = [
            "helm",
            "upgrade",
            "--atomic",
            "--timeout",
            "180s",
            "--history-max",
            "30",
            install_arg,
            "--namespace",
            f"{namespace}",
            "--values",
            "-",
        ]

        if version:
            helm_command += ["--version", version]

        # Add the name and chart
        os_command = helm_command + [f"{name}", f"{chart}"]

        result = run_os_command(os_command, input=yaml.dump(values))
        if result.return_code:
            logger.std(result, raise_exception=raise_exception)
            return result

        logger.success()
        logger.info(f"\tName: {name}")
        logger.info(f"\tNamespace: {namespace}")

        return result
