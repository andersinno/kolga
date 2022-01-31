import os
from unittest import mock

import pytest

from kolga.libs.helm import Helm
from kolga.libs.kubernetes import Kubernetes
from kolga.libs.services.postresql import PostgresqlService

DEFAULT_TRACK = os.environ.get("DEFAULT_TRACK", "stable")

# ======================================================================
# KUBERNETES CLUSTER _AND_ HELM SERVER REQUIRED FROM THIS POINT FORWARD
# ======================================================================


@pytest.mark.k8s
@mock.patch.dict(os.environ, {"K8S_NAMESPACE": "psqlns"})
def test_create_postgresql_database(
    kubernetes: Kubernetes, test_namespace: str, helm: Helm
) -> None:
    helm_test_repo_url = os.environ.get("TEST_HELM_REGISTRY", "http://localhost:8080")
    helm.add_repo("testing", helm_test_repo_url)

    track = DEFAULT_TRACK

    postgresql_service = PostgresqlService(
        track=track, chart="testing/postgresql", chart_version="10.16.1"
    )

    kubernetes.deploy_service(
        service=postgresql_service, namespace=test_namespace, track=track
    )
