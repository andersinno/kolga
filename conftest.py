import pytest
from _pytest.nodes import Item
from environs import Env

pytest_plugins = "tests"


def pytest_runtest_setup(item: Item) -> None:
    env = Env()

    if item.get_closest_marker("k8s") and not env.bool("TEST_CLUSTER_ACTIVE", False):
        pytest.skip("test requires TEST_CLUSTER_ACTIVE to be true")

    if item.get_closest_marker("docker") and not env.bool("TEST_DOCKER_ACTIVE", False):
        pytest.skip("test requires TEST_DOCKER_ACTIVE to be true")

    if item.get_closest_marker("vault") and not env.bool("TEST_VAULT_ACTIVE", False):
        pytest.skip("test requires TEST_VAULT_ACTIVE to be true")
