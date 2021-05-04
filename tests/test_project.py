from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytest

from kolga.libs.project import Project
from kolga.settings import Settings, settings
from kolga.utils.general import env_var_safe_key

from . import MockEnv
from .testcase import override_settings


def test_project_init() -> None:
    project = Project(track="staging")
    assert project


def test_project_defaults() -> None:
    project = Project(track="staging")

    assert project.track == "staging"
    assert (
        project.image
        == "docker-registry:5000/test/testing:2a7958c61a31a38a365aa347147aba2aaaaaaa"
    )
    assert project.secret_name == "testing-staging-testing-secret"
    assert project.secret_data == {}
    assert project.basic_auth_secret_name == ""
    assert project.urls == ""
    assert not project.is_dependent_project
    assert project.dependency_projects == []
    assert project.additional_urls == []


def test_default_empty_dependencies() -> None:
    project = Project(track="staging")
    assert project.dependency_projects == []


@override_settings(
    DEPENDS_ON_PROJECTS="docker-registry:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_project() -> None:
    project = Project(track="staging")
    assert len(project.dependency_projects) == 1
    assert (
        project.dependency_projects[0].image
        == "docker-registry:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
    )


@override_settings(
    DEPENDS_ON_PROJECTS="docker-registry:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_project_host_port() -> None:
    project = Project(track="staging")
    assert len(project.dependency_projects) == 1
    assert project.dependency_projects[0].name == "odin"


@override_settings(
    DEPENDS_ON_PROJECTS="docker-registry/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_project_no_host_port() -> None:
    project = Project(track="staging")
    assert len(project.dependency_projects) == 1
    assert project.dependency_projects[0].name == "odin"


@override_settings(
    DEPENDS_ON_PROJECTS="docker-registry:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_production_like_url() -> None:
    with pytest.raises(ValueError):
        Project(track="staging", url="www.example.com")


@override_settings(
    DEPENDS_ON_PROJECTS="docker-registry:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_url() -> None:
    project = Project(track="staging")
    assert project.secret_data["ODIN_URL"]


@override_settings(
    DEPENDS_ON_PROJECTS="docker-registry:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
@mock.patch.dict(
    "os.environ",
    {
        "ODIN_K8S_SECRET_TESTVAR_1": "odin_test",
        "TESTING_K8S_SECRET_TESTVAR_2": "testing_test",
        "K8S_SECRET_TESTVAR_0": "main_secret",
    },
)
def test_project_prefixed_variable() -> None:
    project = Project(track="staging")
    assert project.secret_data["TESTVAR_2"] == "testing_test"
    assert project.dependency_projects[0].secret_data["TESTVAR_1"] == "odin_test"


def test_project_prefixed_artifact(mockenv: MockEnv) -> None:
    safe_name = env_var_safe_key(settings.PROJECT_NAME)
    project_scoped_secret_prefix = f"{safe_name}_{settings.K8S_SECRET_PREFIX}"
    test_key, test_value = "DATABASE_NAME", "test-project-database"

    with TemporaryDirectory() as service_artifact_folder:
        with open(Path(service_artifact_folder) / "postgres.env", "w") as f:
            f.write(f"{project_scoped_secret_prefix}{test_key}={test_value}\n")

        with mockenv({"SERVICE_ARTIFACT_FOLDER": service_artifact_folder}):
            # ``Settings.__init__()`` has the side-effect of populating the environment
            # with the values from artifact dotenv files. Those values are then read from
            # ``os.environ`` by ``Project.__init__()`` while creating the ``secret_data``.
            _ = Settings()
            project = Project(track="staging")

    assert project.secret_data[test_key] == test_value
