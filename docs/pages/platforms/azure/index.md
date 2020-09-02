# Azure Pipelines

The CI-pipeline has preliminary support for running in [Azure Pipelines](https://azure.microsoft.com/en-us/services/devops/pipelines/). This document points out some differences from how configuring [GitLab's CI/CD pipeline](../gitlab/index.md) works.

## Defining a YAML configuration file

Instead of extending configuration files provided by Kólga, you will need to provide a whole Azure Pipelines YAML file yourself. This document includes a working example file at the end.

## **Configuration variables**

To use the example configuration file, you need to create a Variable Group named `kolga-vars` in the Azure Pipelines Library, and provide values for these variables:

| variable name               | example value                                |
|-----------------------------|----------------------------------------------|
| CONTAINER_REGISTRY          | docker.anders.fi                             |
| CONTAINER_REGISTRY_PASSWORD | [password for logging in CONTAINER_REGISTRY] |
| CONTAINER_REGISTRY_REPO     | docker.anders.fi/devops/azure-kolga-demo     |
| CONTAINER_REGISTRY_USER     | [username for logging in CONTAINER_REGISTRY] |
| KUBERNETES_CONFIG           | [base64 encoded YAML]                        |

KUBERNETES_CONFIG needs to be base64 encoded YAML [kubeconfig configuration](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/). That configuration given in this variable will be passed to kubectl. The configuration should point to the kubecluster where the application is being deployed, and the user defined in the configuration must have admin access to the namespace where the application is being deployed.

An example kubeconfig YAML template, with specific values stripped:

```yaml
apiVersion: v1
clusters:
- cluster:
    server: https://${cluster_hostname}
    certificate-authority-data: ${base64_certificate}
  name: default-cluster
contexts:
- context:
    cluster: default-cluster
    user: default-user
  name: default-context
current-context: default-context
kind: Config
preferences: {}
users:
- name: ${username}
  user:
    token: ${JWT}
```

## **Service connections**

To use the example configuration file as is, your Azure Pipelines project needs to have a Docker service connection defined by the name `docker_anders_fi`. It needs to point to a docker registry where the Kólga docker image is available, by name devops/azure-kolga-demo:master-development.

## **Example YAML file**

```yaml
trigger:
- master

pool:
  vmImage: 'Ubuntu 18.04'

variables:
- group: kolga-vars

resources:
  containers:
  - container: Kolga
    image: devops/azure-kolga-demo:master-development
    endpoint: docker_anders_fi

name:
stages:
- stage: Build
  displayName: Build the app
  jobs:
    - job: build
      container: Kolga
      displayName: Build
      steps:
        - bash: git clone --single-branch --branch azure-pipelines-dev https://github.com/andersinno/kolga.git $(Build.SourcesDirectory)/kolga
          name: clone_kolga
        - bash: ./kolga/devops create_images
          name: build_app
- stage: Review
  displayName: Deploy review environment
  jobs:
    - job: review
      variables:
        BASE_DOMAIN: "andersalumni.fi"
        ENVIRONMENT_SLUG: "hello-world"
        K8S_NAMESPACE: "hello-world"
        ENVIRONMENT_URL: https://$(ENVIRONMENT_SLUG).$(BASE_DOMAIN)
        SERVICE_PORT: 5858
      container: Kolga
      displayName: Deploy
      steps:
        - bash: ls -la && git clone --single-branch --branch azure-pipelines-dev https://github.com/andersinno/kolga.git $(Build.SourcesDirectory)/kolga
          name: clone_kolga
        - bash: ls -la && echo $KUBERNETES_CONFIG | base64 -d > .kubeconfig
          name: create_kubeconfig
        - bash: export KUBECONFIG="$(pwd)/.kubeconfig" && export && pwd && ls -la && source ./kolga/utils/shell_utils.sh && set_docker_host && ./kolga/devops deploy_application --track review
          name: deploy
```