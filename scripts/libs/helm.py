import functools
import operator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

import yaml

from scripts.settings import settings
from scripts.utils.general import kuberenetes_safe_name, run_os_command
from scripts.utils.logger import logger
from scripts.utils.models import SubprocessResult


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

    @staticmethod
    def get_chart_params(flag: str, values: List[Any]) -> List[str]:
        # Create a list of lists with all of the flag and values for the Helm template
        values_params = [[flag, str(value)] for value in values]
        # Flatten the list of lists to a single list
        flattened_value_params: List[str] = functools.reduce(
            operator.iconcat, values_params, []
        )

        return flattened_value_params

    def upgrade_chart(
        self,
        name: str,
        values: Dict[str, Any],
        namespace: str,
        chart: str = "",
        chart_path: Optional[Path] = None,
        values_files: Optional[List[Path]] = None,
        install: bool = True,
        version: Optional[str] = None,
        raise_exception: bool = True,
    ) -> SubprocessResult:
        if chart_path:
            if not chart_path.is_absolute():
                chart_path = settings.devops_root_path / chart_path
            if not chart_path.exists():
                logger.error(
                    message=f"Path '{str(chart_path)}' does not exist",
                    error=OSError(),
                    raise_exception=True,
                )
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
        ]

        if version:
            helm_command += ["--version", version]

        # Add values files
        if values_files:
            helm_command += self.get_chart_params(flag="--values", values=values_files)

        safe_name = kuberenetes_safe_name(name=name)
        values_yaml = yaml.dump(values)

        with NamedTemporaryFile(buffering=0) as fobj:
            fobj.write(values_yaml.encode())
            result = run_os_command(
                [*helm_command, "--values", fobj.name, f"{safe_name}", f"{chart}"],
            )

        if result.return_code:
            logger.std(result, raise_exception=raise_exception)
            return result

        logger.success()
        logger.info(f"\tName: {safe_name} (orig: {name})")
        logger.info(f"\tNamespace: {namespace}")

        return result
