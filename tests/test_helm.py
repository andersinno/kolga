import os

import pytest

from kolga.libs.helm import Helm


@pytest.mark.parametrize(
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


def test_get_chart_params() -> None:
    values = [
        "app=testapp",
        "release=testing",
        "lizard=-1",
        "integer=1324",
        "negative_integer=-234",
    ]

    expected = [
        "--set",
        "app=testapp",
        "--set",
        "release=testing",
        "--set",
        "lizard=-1",
        "--set",
        "integer=1324",
        "--set",
        "negative_integer=-234",
    ]

    assert Helm.get_chart_params("--set", values) == expected


class TestHelmRegistryFunctions:
    helm_repo_name = "localhelm"
    helm_repo_url = os.environ.get("TEST_HELM_REGISTRY", "http://localhost:8080")

    def setup(self) -> None:
        self.helm = Helm()
        self.helm.add_repo(self.helm_repo_name, self.helm_repo_url)
        self.helm.setup_helm()
