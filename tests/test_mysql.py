import os

from kolga.libs.helm import Helm
from kolga.libs.kubernetes import Kubernetes
from kolga.libs.services.mysql import MysqlService

DEFAULT_TRACK = os.environ.get("DEFAULT_TRACK", "stable")
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "testing")

# ======================================================================
# KUBERNETES CLUSTER _AND_ HELM SERVER REQUIRED FROM THIS POINT FORWARD
# ======================================================================


def test_create_mysql_database(
    kubernetes: Kubernetes, test_namespace: str, helm: Helm
) -> None:
    helm_test_repo_url = os.environ.get("TEST_HELM_REGISTRY", "http://localhost:8080")
    helm.add_repo("testing", helm_test_repo_url)

    track = DEFAULT_TRACK

    mysql_service = MysqlService(
        track=track, chart="testing/mysql", chart_version="1.6.6"
    )

    kubernetes.deploy_service(
        service=mysql_service, namespace=test_namespace, track=track
    )
