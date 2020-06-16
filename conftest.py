import os
from typing import Generator

import pytest

from kolga.libs.helm import Helm
from kolga.libs.kubernetes import Kubernetes


@pytest.fixture()  # type: ignore
def kubernetes() -> Kubernetes:
    return Kubernetes()


@pytest.fixture()  # type: ignore
def helm() -> Generator[Helm, None, None]:
    helm = Helm()
    yield helm
    try:
        helm.remove_repo("stable")
    except Exception:
        pass


@pytest.fixture()  # type: ignore
def test_namespace(kubernetes: Kubernetes) -> Generator[str, None, None]:
    namespace = kubernetes.create_namespace()
    yield namespace
    kubernetes.delete_namespace()


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """
    if os.environ.get("TEST_CLUSTER_ACTIVE", 0) not in [1, "1", True, "True"]:
        raise Exception(
            "Kubernetes test cluster sanity check failed. Please make sure "
            "you are using a testing cluster and not production"
        )
