import os
from typing import Generator

import pytest
from _pytest.nodes import Item

from kolga.libs.helm import Helm
from kolga.libs.kubernetes import Kubernetes


@pytest.fixture()
def kubernetes() -> Kubernetes:
    return Kubernetes()


@pytest.fixture()
def helm() -> Generator[Helm, None, None]:
    helm = Helm()
    yield helm
    try:
        helm.remove_repo("stable")
    except Exception:
        pass


@pytest.fixture()
def test_namespace(kubernetes: Kubernetes) -> Generator[str, None, None]:
    namespace = kubernetes.create_namespace()
    yield namespace
    kubernetes.delete_namespace()


def pytest_runtest_setup(item: Item) -> None:
    if item.get_closest_marker("k8s") and os.environ.get(
        "TEST_CLUSTER_ACTIVE", False
    ) not in [1, "1", True, "True"]:
        pytest.skip("test requires TEST_CLUSTER_ACTIVE to be true")

    if item.get_closest_marker("docker") and os.environ.get(
        "TEST_CLUSTER_ACTIVE", False
    ) not in [1, "1", True, "True"]:
        pytest.skip("test requires TEST_DOCKER_ACTIVE to be true")
