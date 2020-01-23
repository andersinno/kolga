from unittest import mock

import pytest

from scripts.libs.project import Project

from .testcase import override_settings


def test_project_init() -> None:
    project = Project(track="staging")
    assert project


def test_project_defaults() -> None:
    project = Project(track="staging")

    assert project.track == "staging"
    assert (
        project.image
        == "localhost:5000/test/testing:2a7958c61a31a38a365aa347147aba2aaaaaaa"
    )
    assert project.secret_name == "testing-staging-secret"
    assert project.secret_data == {}
    assert project.basic_auth_secret_name == ""
    assert project.urls == ""
    assert not project.is_dependent_project
    assert project.dependency_projects == []
    assert (
        str(getattr(getattr(project, "database"), "url"))
        == "postgresql://testuser:testpass@testing-staging-db-postgresql:5432/testdb"
    )
    assert project.additional_urls == []


def test_default_empty_dependencies() -> None:
    project = Project(track="staging")
    assert project.dependency_projects == []


@override_settings(
    DEPENDS_ON_PROJECTS="localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_project() -> None:
    project = Project(track="staging")
    assert len(project.dependency_projects) == 1
    assert (
        project.dependency_projects[0].image
        == "localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
    )


@override_settings(
    DEPENDS_ON_PROJECTS="localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_project_host_port() -> None:
    project = Project(track="staging")
    assert len(project.dependency_projects) == 1
    assert project.dependency_projects[0].name == "odin"


@override_settings(
    DEPENDS_ON_PROJECTS="localhost/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_project_no_host_port() -> None:
    project = Project(track="staging")
    assert len(project.dependency_projects) == 1
    assert project.dependency_projects[0].name == "odin"


@override_settings(
    DEPENDS_ON_PROJECTS="localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_project_postgresql() -> None:
    project = Project(track="staging")
    assert len(project.dependency_projects) == 1
    assert project.dependency_projects[0].database is None


@override_settings(
    DEPENDS_ON_PROJECTS="localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage",
    MYSQL_ENABLED=True,
)
def test_dependency_mysql() -> None:
    project = Project(track="staging")
    assert project.database
    assert len(project.dependency_projects) == 1
    assert project.dependency_projects[0].database is not None
    assert project.dependency_projects[0].database.url.host == project.database.url.host
    assert project.dependency_projects[0].database.url.database == "odin"
    assert (
        project.dependency_projects[0].database.url.username
        != project.database.url.username
    )
    assert (
        project.dependency_projects[0].database.url.password
        != project.database.url.password
    )


@override_settings(
    DEPENDS_ON_PROJECTS="localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_production_like_url() -> None:
    with pytest.raises(ValueError):
        Project(track="staging", url="www.example.com")


@override_settings(
    DEPENDS_ON_PROJECTS="localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
)
def test_dependency_url() -> None:
    project = Project(track="staging")
    assert project.secret_data["ODIN_URL"]


@override_settings(
    DEPENDS_ON_PROJECTS="localhost:5000/test/odin:2a7958c61a31a38a365aa347147aba2aaaaaaa-finalstage"
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
