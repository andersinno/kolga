import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Generator, Iterator, Mapping, Optional

import pytest
from environs import Env
from pytest import MonkeyPatch

from kolga.libs.helm import Helm
from kolga.libs.kubernetes import Kubernetes
from kolga.plugins.base import PluginBase

if TYPE_CHECKING:
    from contextlib import _GeneratorContextManager


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


MockEnv = Callable[
    [Mapping[str, Optional[str]]], "_GeneratorContextManager[os._Environ[str]]"
]


@pytest.fixture
def mockenv(monkeypatch: MonkeyPatch) -> MockEnv:
    @contextmanager
    def inner(env: Mapping[str, Optional[str]]) -> Iterator["os._Environ[str]"]:
        with monkeypatch.context() as m:
            for k, v in env.items():
                if v is None:
                    m.delenv(k, raising=False)
                else:
                    m.setenv(k, v)
            yield os.environ

    return inner
