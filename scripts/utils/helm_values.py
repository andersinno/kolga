from typing import List, TypedDict

from .models import HelmValues


class _Application(TypedDict, total=False):
    database_host: str
    database_url: str
    fileSecretName: str
    fileSecretPath: str
    initializeCommand: str
    migrateCommand: str
    secretName: str
    track: str


class _GitLab(TypedDict, total=False):
    app: str
    env: str


class _Ingress(TypedDict, total=False):
    basicAuthSecret: str
    certManagerAnnotationPrefix: str
    clusterIssuer: str
    maxBodySize: str
    preventRobots: bool


class _Service(TypedDict, total=False):
    targetPort: int
    url: str
    urls: List[str]


class _HPA(TypedDict, total=False):
    avgCpuUtilization: int
    avgRamUtilization: int
    enabled: bool
    maxReplicas: int
    minReplicas: int


class ApplicationDeploymentValues(HelmValues, total=False):
    application: _Application
    gitlab: _GitLab
    hpa: _HPA
    ingress: _Ingress
    image: str
    namespace: str
    releaseOverride: str
    replicaCount: int
    service: _Service


class _TestFramework(TypedDict, total=False):
    enabled: bool


class MySQLDeploymentValues(HelmValues, total=False):
    imageTag: str
    mysqlUser: str
    mysqlPassword: str
    mysqlRootPassword: str
    mysqlDatabase: str
    testFramework: _TestFramework


class _Image(TypedDict, total=False):
    registry: str
    repository: str
    tag: str


class PostgreSQLDeploymentValues(HelmValues, total=False):
    image: _Image
    postgresqlUsername: str
    postgresqlPassword: str
    postgresqlDatabase: str
