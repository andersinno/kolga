import base64
import os
import tempfile
from pathlib import Path

import pytest
from kubernetes.client.rest import ApiException

from kolga.libs.kubernetes import Kubernetes
from kolga.libs.project import Project
from kolga.utils.general import get_deploy_name
from kolga.utils.models import BasicAuthUser

DEFAULT_TRACK = os.environ.get("DEFAULT_TRACK", "stable")
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "testing")


@pytest.mark.parametrize(
    "value, expected", [("400", True), ("500", False), ("300", False), ("200", False)]
)
def test__is_client_error(value: str, expected: bool) -> None:
    assert Kubernetes._is_client_error(value) == expected


def test_labels_to_string() -> None:
    test_labels = {"app": "testapp", "release": "testrelease", "lizard": "-1"}

    expected_string = "app=testapp,release=testrelease,lizard=-1"

    assert Kubernetes.labels_to_string(labels=test_labels) == expected_string


@pytest.mark.parametrize(
    "error, raises_exception",
    [(ApiException(), True), (ApiException(status="403"), False)],
)
def test__handle_api_error(error: ApiException, raises_exception: bool) -> None:
    if raises_exception:
        with pytest.raises(ApiException):
            Kubernetes._handle_api_error(error)
    else:
        Kubernetes._handle_api_error(error)


def test__encode_secret() -> None:
    test_data = {"password": "1234", "username": "user"}

    expected_data = {"password": "MTIzNA==", "username": "dXNlcg=="}

    assert Kubernetes._encode_secret(test_data) == expected_data


def test__b64_encode_file() -> None:
    content = "test:$apr1$35522gYe$r3E.NGo0m0bbOXppHr3g0."
    expected = "dGVzdDokYXByMSQzNTUyMmdZZSRyM0UuTkdvMG0wYmJPWHBwSHIzZzAu"

    with tempfile.NamedTemporaryFile() as f:
        encoded_string = str.encode(content, encoding="UTF-8")
        f.write(encoded_string)
        f.seek(0)
        path = Path(f.name)
        assert Kubernetes._b64_encode_file(path=path) == expected


@pytest.mark.k8s
def test__create_basic_auth_data(kubernetes: Kubernetes) -> None:
    basic_auth_users = [
        BasicAuthUser(username="test", password="test"),
        BasicAuthUser(username="user", password="pass"),
    ]

    data = kubernetes._create_basic_auth_data(basic_auth_users=basic_auth_users)
    auth_data = data["auth"]

    decoded_data = base64.b64decode(auth_data).decode("UTF-8")
    user_split = decoded_data.split("\n")[:-1]

    for i, user in enumerate(user_split):
        username, password = user.split(":")
        assert password
        assert username == basic_auth_users[i].username


# =====================================================
# KUBERNETES CLUSTER REQUIRED FROM THIS POINT FORWARD
# =====================================================


@pytest.mark.k8s
def test_create_client(kubernetes: Kubernetes) -> None:
    assert kubernetes


@pytest.mark.k8s
def test_create_namespace_env(kubernetes: Kubernetes, test_namespace: str) -> None:
    assert test_namespace == K8S_NAMESPACE


@pytest.mark.k8s
def test_create_namespace_named(kubernetes: Kubernetes) -> None:
    namespace = "testing-2"
    assert kubernetes.create_namespace(namespace) == namespace
    kubernetes.delete_namespace(namespace)


@pytest.mark.k8s
def test_create_secret_stable(kubernetes: Kubernetes, test_namespace: str) -> None:
    track = DEFAULT_TRACK
    data = {"test_secret": "1234"}
    project = Project(track=track)
    kubernetes.create_secret(
        data=data,
        namespace=K8S_NAMESPACE,
        track=track,
        project=project,
        secret_name=project.secret_name,
    )
    kubernetes.get(resource="secret", namespace=K8S_NAMESPACE, name=project.secret_name)


@pytest.mark.k8s
def test_create_secret_qa(kubernetes: Kubernetes, test_namespace: str) -> None:
    track = "qa"
    project = Project(track=track)
    kubernetes.create_secret(
        data={"test_secret": "1234"},
        namespace=K8S_NAMESPACE,
        track=track,
        project=project,
        secret_name=project.secret_name,
    )
    kubernetes.get(resource="secret", namespace=K8S_NAMESPACE, name=project.secret_name)


@pytest.mark.k8s
def test_delete_namespace(kubernetes: Kubernetes, test_namespace: str) -> None:
    kubernetes.delete(
        resource="namespace", name=test_namespace, namespace=K8S_NAMESPACE
    )
    with pytest.raises(Exception):
        kubernetes.get(resource="namespace", name=test_namespace)


@pytest.mark.k8s
def test_delete_all(kubernetes: Kubernetes, test_namespace: str) -> None:
    track = DEFAULT_TRACK
    deploy_name = get_deploy_name(track=track)
    project = Project(track=track)
    kubernetes.create_secret(
        data={"test": "test"},
        namespace=test_namespace,
        track=track,
        project=project,
        secret_name=project.secret_name,
    )

    kubernetes.delete_all(namespace=test_namespace, labels={"release": deploy_name})

    with pytest.raises(Exception):
        kubernetes.get(resource="secret", name=test_namespace)


@pytest.mark.k8s
def test_create_default_networkpolicy(
    kubernetes: Kubernetes, test_namespace: str
) -> None:
    kubernetes.create_default_network_policy(namespace=K8S_NAMESPACE)
    kubernetes.get(
        resource="networkpolicy",
        namespace=K8S_NAMESPACE,
        name="deny-traffic-from-other-namespaces",
    )
