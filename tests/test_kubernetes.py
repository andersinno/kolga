import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from kubernetes.client.rest import ApiException

from scripts.libs.helm import Helm
from scripts.libs.kubernetes import Kubernetes
from scripts.utils.general import get_deploy_name, get_secret_name

DEFAULT_TRACK = os.environ.get("DEFAULT_TRACK", "stable")
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "testing")


@pytest.mark.parametrize(  # type: ignore
    "value, expected", [("400", True), ("500", False), ("300", False), ("200", False)]
)
def test__is_client_error(value: str, expected: bool) -> None:
    assert Kubernetes._is_client_error(value) == expected


def test_labels_to_string() -> None:
    test_labels = {"app": "testapp", "release": "testrelease", "lizard": "-1"}

    expected_string = "app=testapp,release=testrelease,lizard=-1"

    assert Kubernetes.labels_to_string(labels=test_labels) == expected_string


@pytest.mark.parametrize(  # type: ignore
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


def test_get_environments_secrets_by_prefix() -> None:
    prefix = f"TEST_{str(uuid4())}_SECRET_"

    env_vars = {f"{prefix}PASSWORD": "pass", f"{prefix}LIZARD": "-1"}
    secrets = {f"PASSWORD": "pass", f"LIZARD": "-1"}

    for key, secret in env_vars.items():
        os.environ[key] = secret

    assert Kubernetes.get_environments_secrets_by_prefix(prefix) == secrets


def test__b64_encode_file() -> None:
    content = "test:$apr1$35522gYe$r3E.NGo0m0bbOXppHr3g0."
    expected = "dGVzdDokYXByMSQzNTUyMmdZZSRyM0UuTkdvMG0wYmJPWHBwSHIzZzAu"

    with tempfile.NamedTemporaryFile() as f:
        encoded_string = str.encode(content, encoding="UTF-8")
        f.write(encoded_string)
        f.seek(0)
        path = Path(f.name)
        assert Kubernetes._b64_encode_file(path=path) == expected


# =====================================================
# KUBERNETES CLUSTER REQUIRED FROM THIS POINT FORWARD
# =====================================================


def test_create_client(kubernetes: Kubernetes) -> None:
    assert kubernetes


def test_create_namespace_env(kubernetes: Kubernetes, test_namespace: str) -> None:
    assert test_namespace == K8S_NAMESPACE


def test_create_namespace_named(kubernetes: Kubernetes) -> None:
    namespace = "testing-2"
    assert kubernetes.create_namespace(namespace) == namespace
    kubernetes.delete_namespace(namespace)


def test_create_secret_stable(kubernetes: Kubernetes, test_namespace: str) -> None:
    track = DEFAULT_TRACK
    expected_secret_name = get_secret_name(track)
    data = {"test_secret": "1234"}
    secret_result = kubernetes.create_secret(
        data=data, namespace=K8S_NAMESPACE, track=track
    )
    assert secret_result == expected_secret_name


def test_create_secret_qa(kubernetes: Kubernetes, test_namespace: str) -> None:
    track = "qa"
    expected_secret_name = get_secret_name(track)
    secret_result = kubernetes.create_secret(
        data={"test_secret": "1234"}, namespace=K8S_NAMESPACE, track=track
    )
    assert secret_result == expected_secret_name
    kubernetes.get(
        resource="secret", namespace=K8S_NAMESPACE, name=expected_secret_name
    )


def test_create_secrets_from_environment(
    kubernetes: Kubernetes, test_namespace: str
) -> None:
    track = "mtest-fro-env"
    expected_secret_name = get_secret_name(track)
    secret_result = kubernetes.create_secrets_from_environment(
        namespace=K8S_NAMESPACE, track=track
    )
    assert secret_result == expected_secret_name
    kubernetes.get(
        resource="secret", namespace=K8S_NAMESPACE, name=expected_secret_name
    )


def test_delete_namespace(kubernetes: Kubernetes, test_namespace: str) -> None:
    kubernetes.delete(
        resource="namespace", name=test_namespace, namespace=K8S_NAMESPACE
    )
    with pytest.raises(Exception):
        kubernetes.get(resource="namespace", name=test_namespace)


def test_delete_all(kubernetes: Kubernetes, test_namespace: str) -> None:
    track = DEFAULT_TRACK
    deploy_name = get_deploy_name(track=track)
    kubernetes.create_secrets_from_environment(namespace=test_namespace, track=track)

    kubernetes.delete_all(namespace=test_namespace, labels={"release": deploy_name})

    with pytest.raises(Exception):
        kubernetes.get(resource="secret", name=test_namespace)


# ======================================================================
# KUBERNETES CLUSTER _AND_ HELM SERVER REQUIRED FROM THIS POINT FORWARD
# ======================================================================


def test_create_postgres_database(
    kubernetes: Kubernetes, test_namespace: str, helm: Helm
) -> None:
    helm_test_repo_url = os.environ.get("TEST_HELM_REGISTRY", "http://localhost:8080")
    helm.add_repo("testing", helm_test_repo_url)
    track = DEFAULT_TRACK
    kubernetes.create_postgres_database(
        namespace=test_namespace, track=track, helm_chart="testing/postgresql"
    )


def test_create_mysql_database(
    kubernetes: Kubernetes, test_namespace: str, helm: Helm
) -> None:
    helm_test_repo_url = os.environ.get("TEST_HELM_REGISTRY", "http://localhost:8080")
    helm.add_repo("testing", helm_test_repo_url)
    track = DEFAULT_TRACK
    kubernetes.create_mysql_database(
        namespace=test_namespace, track=track, helm_chart="testing/mysql"
    )
