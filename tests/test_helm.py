import os

import pytest

from scripts.libs.helm import Helm


@pytest.mark.parametrize(  # type: ignore
    "value, expected",
    [
        ("charts/testing", "testing"),  # Stable is a special case
        ("charts//testing", "testing"),
        ("testing", "testing"),
        ("charts/testing/lizard", "lizard"),
    ],
)
def test_get_chart_name_strings(value: str, expected: str) -> None:
    assert Helm.get_chart_name(value) == expected


def test_get_chart_name_exception() -> None:
    with pytest.raises(ValueError):
        Helm.get_chart_name("")


class TestHelmRegistryFunctions:
    helm_repo_name = "localhelm"
    helm_repo_url = os.environ.get("TEST_HELM_REGISTRY", "http://localhost:8080")

    def setup(self) -> None:
        self.helm = Helm()
        self.helm.add_repo(self.helm_repo_name, self.helm_repo_url)
        self.helm.setup_helm()
