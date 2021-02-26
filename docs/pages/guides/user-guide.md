# User Guide

This guide is meant to be more in-depth than the [](/pages/tutorials/getting-started)
tutorial but not as overwhelming as the [](/pages/reference/index). It lists the most
commonly used functionalities and concepts.


## Commonly used configuration variables

Defining environment variables varies from CI/CD automation platform to another. Check
your platform's documentation for more information, e.g.:

* [Azure Pipelines](https://docs.microsoft.com/en-us/azure/devops/pipelines/get-started/)
* [GitHub Actions](https://docs.github.com/en/actions)
* [GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)

See [the reference](/pages/reference/variables) and for list of all known variables, and
[](/pages/reference/platforms/index) for platform-specific configuration options.


### Application settings

* `APP_INITIALIZE_COMMAND`

    * Command to run on first start

* `APP_MIGRATE_COMMAND`

    * Command to run on every update

* `SERVICE_PORT`

    * Port that application listens on


### Docker-related variables

* `DOCKER_BUILD_CONTEXT`

    * Build context folder

* `DOCKER_BUILD_SOURCE`

    * Dockerfile to build from

* `DOCKER_BUILD_ARG_`

    * Variables prefixed with `DOCKER_BUILD_ARG_` are passed to `docker image
      build`. The prefix is stripped (e.g. `DOCKER_BUILD_ARG_FOO=bar` will become
      `--build-arg FOO=bar`).


### Kubernetes-related variables

* `K8S_LIVENESS_PATH`

    * Endpoint for Kubernetes liveness probes (default `/healthz`). Liveness probes are
      used to know when to restart a container. For example, liveness probes could catch
      a deadlock, where an application is running, but unable to make progress.

* `K8S_READINESS_PATH`

    * Endpoint for Kubernetes readiness probes (default `/readiness`). Readiness probes
      are used to know when a container is ready to start accepting traffic. A Pod is
      considered ready when all of its containers are ready

* `K8S_LIVENESS_FILE`

    * Check for existence of a file instead of doing a HTTP GET on `K8S_LIVENESS_PATH`
      endpoint.

* `K8S_READINESS_FILE`

    * Check for existence of a file instead of doing a HTTP GET on `K8S_READINESS_PATH`
      endpoint.


## Secrets

Secrets are used to configure the deployed application. This includes, for example
settings database address and password, passing allowed hosts to a Django app, etc.

There are two kinds of secrets: secrets that are passed in as environment variables, and
secrets that are stored in filesystem.


### Environment variables

Variables prefixed with `K8S_SECRET_` are passed to the application as environment
variables. The prefix is stripped, e.g. setting `K8S_SECRET_FOO=bar` will create an
environment variable `FOO` with `bar` as it's value.


### File secrets

Variables prefixed with `K8S_FILE_SECRET_` are passed to the application as files on the
containers filesystem. The prefix is stripped and the corresponding environment variable
will contain the path is the file.

For example, `K8S_FILE_SECRET_FOO=bar` will create a file with the string `bar` as it's
contents, and an environment variable named `FOO` containing the path of the file
(e.g. `FOO=/tmp/secrets/foo`).


## Platform-specific notes

### GitLab CI/CD

#### Passing variables

Variables can be defined in project's CI/CD settings and in `.gitlab-ci.yml` as global
variables or per-job variables.

```yaml
variables:
  # Global variables go here
  K8S_LIVENESS_FILE: '/tmp/look-alive'

review:
  variables:
    # Per-job variables for `review` job
    K8S_SECRET_DEBUG: 1
```


#### Pre-defined stages and jobs

Kólga provides a base template for use with GitLab CI/CD that can be included in
project's own `.gitlab-ci.yml`. The template provides the following stages, all of which
are optional and overridable. See [the reference](/pages/reference/stages) for a more
detailed description.

* `build` stage: `.build` job template

    * Builds the Docker images to be used in later stages. By default a tag is created
      for every stage in a multi-stage `Dockerfile`.

* `test` stage: `.test` job template

    * Tests are not mandated by the pipeline. Every project is different and the
      pipeline does not put any restrictions on what types of tests, if any, are to be
      run. By default the tests are run using an image that matches `development` stage
      in the `Dockerfile`.

* `review-service` stage: `.review-service` job template

    * Deploy extra services that will run alongside the main application project, for
      example PostgreSQL, MySQL or RabbitMQ.

* `review` stage: `review` job

    * Review environments are deployments, by default, done for every merge request to
      create developers and reviewers a live environment to test before merging. These
      environments are non-persistent and made to be completely removed when the code
      has been merged.

* `staging` stage: `staging` job

    * A staging or QA environment is intended to be the last stage of quality assurance
      testing before the final release of software. This environment usually resembles
      the production environment very closely and usually uses same third party services
      as the production environment. For this reason, a non-persistent database
      environment is highly discouraged.

* `production` stage: `production` job

    * Deploy the application to a production environment. By default this job is
      triggered for tags that match the pattern `r-[0-9]+`.


Jobs prefixed with a dot (e.g. `.build`) are not run but are intended to be extended
when writing a CI/CD configuration for a project. For example:

```yaml
build:
  extends: .build
```
