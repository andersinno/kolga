from unittest import mock

import pytest

from kolga.libs.project import Project

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
