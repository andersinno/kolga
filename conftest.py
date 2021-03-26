import os
from typing import Any, Generator

import pytest
from _pytest.nodes import Item
from environs import Env

from kolga.hooks.plugins import PluginBase
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


@pytest.fixture()
def test_plugin() -> type:
    def plugin_constructor(self: Any, env: Env) -> None:
        self.required_variables = [("TEST_PLUGIN_VARIABLE", env.str)]
        self.configure(env=env)

    TestFixturePlugin = type(
        "TestFixturePlugin",
        (PluginBase,),
        {
            # constructor
            "__init__": plugin_constructor,
            "name": "test_fixture_plugin",
            "verbose_name": "Kolga Test Plugin",
            "version": 0.1,
        },
    )
    return TestFixturePlugin


def pytest_runtest_setup(item: Item) -> None:
    if item.get_closest_marker("k8s") and os.environ.get(
        "TEST_CLUSTER_ACTIVE", False
    ) not in [1, "1", True, "True"]:
        pytest.skip("test requires TEST_CLUSTER_ACTIVE to be true")

    if item.get_closest_marker("docker") and os.environ.get(
        "TEST_DOCKER_ACTIVE", False
    ) not in [1, "1", True, "True"]:
        pytest.skip("test requires TEST_DOCKER_ACTIVE to be true")
