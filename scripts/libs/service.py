from pathlib import Path
from typing import List, Mapping, Optional, Set

from scripts.utils.general import get_project_secret_var
from scripts.utils.models import HelmValues


class Service:
    """
    A service is a by Helm deployable software

    A service takes care of storing the configuration needed
    to deploy a service to Kubernetes. It also stores metadata
    about the service so that it can be shared with other services
    if need be.
    """

    def __init__(
        self,
        name: str,
        track: str,
        values: Optional[HelmValues] = None,
        artifact_name: Optional[str] = None,
        values_files: Optional[List[Path]] = None,
        chart: str = "",
        chart_path: Optional[Path] = None,
        chart_version: Optional[str] = None,
        depends_on: Optional[Set["Service"]] = None,
    ) -> None:
        self.name = name
        self.track = track
        self.values = values or {}
        self.artifact_name = artifact_name
        self.values_files: List[Path] = values_files or []
        self.chart = chart
        self.chart_path = chart_path
        self.chart_version = chart_version
        self.depends_on: Set["Service"] = depends_on or set()
        self._prerequisite_of: Set["Service"] = set()
        self._validate_chart()

    def _validate_chart(self) -> None:
        if not self.chart and not self.chart_path:
            raise ValueError("Either chart or chart_name must be defined")

    def add_dependency(self, service: "Service") -> None:
        self.depends_on.add(service)
        service.add_prerequisite(self)

    def add_prerequisite(self, service: "Service") -> None:
        self._prerequisite_of.add(service)
        if self not in service.depends_on:
            service.add_dependency(self)

    def setup_prerequisites(self) -> None:
        pass

    def get_artifacts(self) -> Mapping[str, str]:
        return {}

    def get_service_secret_artifact_name(self, service: "Service") -> str:
        if not self.artifact_name:
            raise ValueError(f"No artifact name set for the service {self.name}")

        return get_project_secret_var(
            project_name=service.name, value=self.artifact_name
        )
