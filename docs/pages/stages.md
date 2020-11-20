# Stages

While the stages in a CI tool might differ slightly, the there are five main parts of most pipelines. However, these steps might be duplicated multiple times, or contain multiple smaller jobs.

## Build

Builds the Docker images to be used in later stages or to be used for debugging the application locally.

### Commands

**DevOps CLI**

The `create_images` command that can be used to create Docker images. By default it looks for a `Dockerfile` in the root of the project.

>`create_images` updates Git submodules before building

>`create_images` logs in to a Docker registry before building

**Configuration:**

| Variable               | Default    | Description                                                                                                               |
|------------------------|------------|---------------------------------------------------------------------------------------------------------------------------|
| `DOCKER_BUILD_SOURCE`  | Dockerfile | Specifies which Dockerfile to build                                                                                       |
| `DOCKER_BUILD_CONTEXT` | .          | Specifies which build context to use when building                                                                        |
| `DOCKER_IMAGE_NAME`    |            | Name of the subproject to build. This will be added to the path of the final image.<br> See "Image naming" for an example. |


### Image naming

By default, images are named according to the following structure are created:

`<IMAGE_REGISTRY>/<PROJECT_NAME>[/<DOCKER_IMAGE_NAME>]:[-<STAGE>]<COMMIT_HASH>`

`<IMAGE_REGISTRY>/<PROJECT_NAME>[/<DOCKER_IMAGE_NAME>]:[-<STAGE>]<COMMIT_REF>`

> For more information regarding `DOCKER_IMAGE_NAME` read the "Mono-repos/Multi-project repositories" section.
> For more information regarding `STAGE` read the "Multi-stage builds" section

### Multi-stage builds

When building container images, often images are split up into stages. This is what Docker calls a  [multi-stage build](https://docs.docker.com/develop/develop-images/multistage-build/). By default, the pipeline builds and store all stages of the Dockerfile as separate images in a registry.

What this means in practise is that if a Dockerfile contains multiple `FROM x AS y` statements, an image will be build and postfixed with `y` for each stage, also the last stage of an image.

**Example:**

Let's say we have a project with the following Dockerfile and 

    FROM python:3.7 AS appbase
    
    ...
    
    FROM appbase AS development
    
    ...
    
    FROM appbase AS production

The following tags will be build (the container registry and image name has been omitted for clarity):

- `:<HASH>-appbase`
- `:<HASH>-development`
- `:<HASH>-production`
- `:<HASH>` (identical to the `-production` image)

### CI specific configurations

- **GitLab**

### Mono-repos/Multi-project repositories

To build multiple projects inside the same repository, the image, context and name of the image needs to be set for each build. This can be configured with the three variables mentioned in the "Commands" section.

**Example:**

You have a project `Flower` that contains two sub-projects `Sunflower` and `Rose` with the following file structure:

    flower/
    ├── sunflower/
    │   └── Dockerfile
    └── rose/
        └── Dockerfile

To build Docker images for both project, the build command would need to be run twice. This could be done either running the build command twice in the same CI job or splitting it up into two jobs. The build commands do not rely on each-other.

The following could be run to build both images:

    > export DOCKER_BUILD_SOURCE=/flower/sunflower/Dockerfile
    > export DOCKER_BUILD_CONTEXT=/flower/sunflower
    > export DOCKER_IMAGE_NAME=sunflower
    > devops create_images
    ...
    > export DOCKER_BUILD_SOURCE=/flower/rose/Dockerfile
    > export DOCKER_BUILD_CONTEXT=/flower/rose
    > export DOCKER_IMAGE_NAME=rose
    > devops create_images
    ...

The CI tool used might have a way to set environment variables in a different way which might make more sense and create a better structured flow.

## Test

Tests are not part of the pipeline per-se, every project is different and the pipeline does not put any restrictions on what types of tests are to be run during a projects CI stage. The default CI/CD runner image does provide defaults for runnings tests however so that the process can be more consistent across projects.

### Commands

**DevOps CLI**

The `test_setup` command that can be used to pull a previously built image that can be used for testing.

> `test_setup` updates Git submodules before building

> `test_setup` logs in to a Docker registry before building

**Configuration:**

| Variable                      | Default     | Description                                                                                                              |
|-------------------------------|-------------|--------------------------------------------------------------------------------------------------------------------------|
| `DOCKER_TEST_IMAGE_STAGE`     | development | Specifies which stage image should be pulled when the `test_setup` command is run                                        |
| `DOCKER_IMAGE_NAME`           |             | Name of the subproject to pull. <br>This will be added to the path of the final image. See "Image naming" for an example.|


### Consistency and pre-defined pipelines

For the sake of consistency, all pre-defined CI configurations found in this project run `make test` as the default command after pulling the test image though `devops test_setup`. If this is not the preferred way of the project using the pre-defined pipeline, then the test job should be overridden/extended.

### CI specific configurations

- **GitLab**


## Review service

Deploy extra services that will run alongside the main application project.

To create a review service, add a job that `extends: .review-service` and then in the `scripts` part
the DevOps CLI command `deploy_service` should be called to deploy a service.

Example:

```
service-mysql:
  extends: .review-service
  script:
    - devops deploy_service --track review --service mysql --env_var DATABASE_URL --projects my_api, some_backend
  only:
    - master
```

### Commands

**DevOps CLI**

The `deploy_service` command that can be used to deploy a service to a Kubernetes cluster. For each service that
is to be deployed, a separate `review_service` job should be specified.


**Parameters:**

| Variable           | Default     | Description                                                                                   |
|--------------------|-------------|-----------------------------------------------------------------------------------------------|
| `-t / --track`     | review      | Specifies which track to run on, defaults to `review`, and should most likely not be changed. |
| `-s / --service`   |             | Name of the service to deploy, such as `mysql`, `postgresql`, `rabbitmq`.                     |
| `-e / --env-var`    |             | Specifies what environment name will get passed as the connection URI to the project.         |
| `-p / --projects`  |             | Comma separated list of the projects that should get access to the service.                   |


| Variable                 | Default | Description                                                                                                                                                                                                                                                                                                                                            |
|--------------------------|---------|--------------------------------------------------|
| `POSTGRES_VERSION_TAG`   | 9.6     | Version of PostgreSQL to use if deployed        |
| `MYSQL_VERSION_TAG`      | 5.7     | Version of MySQL to user if deployed            |


## Review

Review environments are deployments done at the pull/merge request stage to make the review more interactive and let the reviewers and the coder get a live environment to test before merging. These environments are non-persistent and made to be completely removed when the code has been merged.

### Commands

**DevOps CLI**

The `deploy_application` command is share across all deployment stages, and is therefor also used for deploying review environments. In the case of the review the argument `--track review` is recommended to be to give the deployment a distinctive name when deployed to the Kubernetes cluster.

**Configuration**

| Variable                 | Default | Description                                                                                                                                                                                                                                                                                                                                            |
|--------------------------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ENVIRONMENT_SLUG`       |         | The slug name of the environment. This will be injected as `releaseOverride` in <br> the Helm chart and in the defaultHelm chart this will be set as the `release` <br> label for the Deployment.                                                                                                                                                         |
| `ENVIRONMENT_URL`        |         | The URL of the final environment. This needs to be a URL that the Kubernetes  <br> cluster can actually manage and create SSL certificates for. This will be injected <br> as `service.url` in the Helm chart and in the default Helm chart this will be set <br> as the `host` value for the Ingress.                                                           |
| `SERVICE_PORT`           | 8000    | The port that the application listens to. This will be injected as `service.port` <br> in the Helm chart and in the default Helm chart this will be set as the <br> `targetPort` value for the Service.                                                                                                                                                    |
| `K8S_NAMESPACE`          |         | The namespace that the application is deployed to. This namespace will be created <br> as part of the deployment and the service account needs to have privileges <br> to create such a namespace. <br> This will be injected as `namespace` in the Helm chart <br> and in the default Helm chart this will be set as the namespace for all deployed manifests. |
| `APP_INITIALIZE_COMMAND` |         | Command to run inside the container when it is deployed for the very first time. <br> This will be run as a Job inside the cluster and will only run once. It will run <br> before the deployment of the application happens.                                                                                                                              |
| `APP_MIGRATE_COMMAND`    |         | Command to run inside the container when the application is deployed, be it initial <br> installation or upgrades. This will be run as a Job inside the cluster, all previous Jobs will <br> be deleted on upgrades. It will run  each time when the application is deployed.                                                                           |


### CI specific configurations

- **GitLab**

## QA/Staging

A staging or QA environment works close-to-final stage for quality assurance testing before the final release of a software. This environment usually reassembles the production environment very closely and usually uses same third party service as the production environment. For this reason, a non-persistent database environment is highly discouraged.

Note that the same command that deploys the preview environment, also deploys the staging and therefor supports the same environment variables. However, settings either of the database environment variables in this stage is once again *highly discourages* due to their non-persistent nature.

### Commands

**DevOps CLI**

The `deploy_application` command is share across all deployment stages, and is therefor also used for deploying review environments. In the case of the review the argument `--track review` is recommended to be to give the deployment a distinctive name when deployed to the Kubernetes cluster.

**Configuration**

| Variable                 | Default | Description                                                                                                                                                                                                                                                                                                                                            |
|--------------------------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ENVIRONMENT_SLUG`       |         | The slug name of the environment. This will be injected as `releaseOverride` in <br> the Helm chart and in the defaultHelm chart this will be set as the `release` <br> label for the Deployment.                                                                                                                                                         |
| `ENVIRONMENT_URL`        |         | The URL of the final environment. This needs to be a URL that the Kubernetes  <br> cluster can actually manage and create SSL certificates for. This will be injected <br> as `service.url` in the Helm chart and in the default Helm chart this will be set <br> as the `host` value for the Ingress.                                                           |
| `SERVICE_PORT`           | 8000    | The port that the application listens to. This will be injected as `service.port` <br> in the Helm chart and in the default Helm chart this will be set as the <br> `targetPort` value for the Service.                                                                                                                                                    |
| `K8S_NAMESPACE`          |         | The namespace that the application is deployed to. This namespace will be created <br> as part of the deployment and the service account needs to have privileges <br> to create such a namespace. <br> This will be injected as `namespace` in the Helm chart <br> and in the default Helm chart this will be set as the namespace for all deployed manifests. |
| `APP_INITIALIZE_COMMAND` |         | Command to run inside the container when it is deployed for the very first time. <br> This will be run as a Job inside the cluster and will only run once. It will run <br> before the deployment of the application happens.                                                                                                                              |
| `APP_MIGRATE_COMMAND`    |         | Command to run inside the container when the application is deployed, be it initial <br> installation or upgrades. This will be run as a Job inside the cluster, all previous Jobs will <br> be deleted on upgrades. It will run  each time when the application is deployed.                                                                           |

### CI specific configurations

- **GitLab**

## Production

Deploy the application to a production environment. Same thing applies as with the review environment, enabling databases through environment variables is highly discouraged.

### Commands

**DevOps CLI**

The `deploy_application` command is share across all deployment stages, and is therefor also used for deploying review environments. In the case of the review the argument `--track review` is recommended to be to give the deployment a distinctive name when deployed to the Kubernetes cluster.

**Configuration**

| Variable                 | Default | Description                                                                                                                                                                                                                                                                                                                                            |
|--------------------------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ENVIRONMENT_SLUG`       |         | The slug name of the environment. This will be injected as `releaseOverride` in <br> the Helm chart and in the defaultHelm chart this will be set as the `release` <br> label for the Deployment.                                                                                                                                                         |
| `ENVIRONMENT_URL`        |         | The URL of the final environment. This needs to be a URL that the Kubernetes  <br> cluster can actually manage and create SSL certificates for. This will be injected <br> as `service.url` in the Helm chart and in the default Helm chart this will be set <br> as the `host` value for the Ingress.                                                           |
| `SERVICE_PORT`           | 8000    | The port that the application listens to. This will be injected as `service.port` <br> in the Helm chart and in the default Helm chart this will be set as the <br> `targetPort` value for the Service.                                                                                                                                                    |
| `K8S_NAMESPACE`          |         | The namespace that the application is deployed to. This namespace will be created <br> as part of the deployment and the service account needs to have privileges <br> to create such a namespace. <br> This will be injected as `namespace` in the Helm chart <br> and in the default Helm chart this will be set as the namespace for all deployed manifests. |
| `APP_INITIALIZE_COMMAND` |         | Command to run inside the container when it is deployed for the very first time. <br> This will be run as a Job inside the cluster and will only run once. It will run <br> before the deployment of the application happens.                                                                                                                              |
| `APP_MIGRATE_COMMAND`    |         | Command to run inside the container when the application is deployed, be it initial <br> installation or upgrades. This will be run as a Job inside the cluster, all previous Jobs will <br> be deleted on upgrades. It will run  each time when the application is deployed.                                                                           |

### CI specific configurations

- **GitLab**

## Network policy

All applications are deployed in their own namespace in Kubernetes. Services can connect to other services in the same namespace but traffic coming from other namespaces is blocked by network policies.
