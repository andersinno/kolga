# Variables

## Overview

An environment variable is a dynamic-named value that can affect the way running processes will
behave on an operating system.

Variables are useful for customizing the CI/CD pipeline as it makes the pipeline more
flexible and easier to configure. It also means less hardcoded values.

## Predefined variables

The DevOps pipeline is build to be able to run existing CI/CD platforms such as GitLab CI,
Travis and CircleCI. It utilizes the variables exposed by those platforms and unifies
them into a set of predefined variables in the DevOps pipeline.

For instance, GitLab exposes a variables named `CI_COMMIT_SHA`. While the name does not
contain anything pointing to GitLab itself, it is uncertain if this variable name is used
on other platforms, for that reason we add a variable `GIT_COMMIT_SHA` which always will
point to the SHA of a commit, no matter the underlying platform, as long as the platform
supplies a predefined variables with the SHA.


| Variable                      | Description                                         | Default                      | CI Support |
|-------------------------------|-----------------------------------------------------|------------------------------|------------|
| BUILDKIT\_CACHE\_REPO         | Cache subrepository for buildkit / buildx           | cache                        |            |
| CONTAINER\_REGISTRY           | Docker registry URL                                 |                              | GitLab     |
| CONTAINER\_REGISTRY\_PASSWORD | Password for Docker registry                        |                              | GitLab     |
| CONTAINER\_REGISTRY\_REPO     | Docker repository for project                       |                              | Gitlab     |
| CONTAINER\_REGISTRY\_USER     | Username for Docker registry                        |                              | GitLab     |
| DATABASE\_DB                  | Database name for preview environment               | appdb                        |            |
| DATABASE\_PASSWORD            | Database password for preview environment           | UUID value                   |            |
| DATABASE\_USER                | Database user for preview environment               | user                         |            |
| DEFAULT\_TRACK                | Track name used if not explicitly set               | stable                       |            |
| DOCKER\_BUILD\_ARG\_PREFIX    | Docker build-arg environment variable prefix        | DOCKER\_BUILD\_ARG\_         |            |
| DOCKER\_BUILD\_CONTEXT        | Build context folder                                | .                            |            |
| DOCKER\_BUILD\_SOURCE         | Dockerfile to build from                            | Dockerfile                   |            |
| DOCKER\_HOST                  | Docker runtime                                      |                              |            |
| DOCKER\_IMAGE\_NAME           | Name of docker image \(without tag\)                | $PROJECT\_NAME               |            |
| DOCKER\_IMAGE\_TAGS           | List of tags to tag the image with when building    | $GIT\_COMMIT\_REF\_NAME      |            |
| DOCKER\_TEST\_IMAGE\_STAGE    | Which image stage to run tests on                   | development                  |            |
| ENVIRONMENT\_SLUG             | Slug name of CI environment                         |                              | GitLab     |
| ENVIRONMENT\_URL              | Full URL to the upcoming environment                |                              | GitLab     |
| GIT\_COMMIT\_REF\_NAME        | The branch or tag name for which project is built   |                              | GitLab     |
| GIT\_COMMIT\_SHA              | Current commits SHA                                 |                              | GitLab     |
| GIT\_DEFAULT\_TARGET\_BRANCH  | Default branch that is targeted for merges          | master                       | GitLab     |
| GIT\_TARGET\_BRANCH           | Target branch for the specific merge/pull-request   |                              | GitLab     |
| K8S\_ADDITIONAL\_HOSTNAMES    | Additional hostnames for the application            |                              |            |
| K8S\_CLUSTER\_ISSUER          | The name of the clusterIssuer to be used by ingress |                              |            |
| K8S\_HPA\_ENABLED             | Enable autoscaling of the Kubernetes deployment     | false                        |            |
| K8S\_HPA\_MAX\_REPLICAS       | Maximum amount of autoscaling replicas to create    | 3                            |            |
| K8S\_HPA\_MIN\_REPLICAS       | Minimum amount of autoscaling replicas to create    | 1                            |            |
| K8S\_HPA\_MAX\_CPU\_AVG       | Average CPU % threshold for when to start scaling   |                              |            |
| K8S\_HPA\_MAX\_RAM\_AVG       | Average RAM % threshold for when to start scaling   |                              |            |
| K8S\_INGRESS\_ANNOTATIONS     | Additional annotations to ingress, ex. k1=v1,k2=v2  |                              |            |
| K8S\_INGRESS\_BASE\_DOMAIN    | Kubernetes default base domain for preview          |                              | GitLab     |
| K8S\_INGRESS\_BASIC\_AUTH     | Space delimited basic auth cred, ex. foo:bar df:aa  |                              |            |
| K8S\_INGRESS\_DISABLED        | Disable ingress deployment                          | False                        |            |
| K8S\_INGRESS\_MAX\_BODY\_SIZE | Set max body size for requests to the nginx ingress | 100m                         |            |
| K8S\_INGRESS\_PREVENT\_ROBOTS | Add a basic robots.txt to disallow all robots       | False                        |            |
| K8S\_NAMESPACE                | Kubernetes namespace to use                         |                              | GitLab     |
| K8S\_PROBE\_FAILURE\_THRESHOLD| How many times a probe can fail                     | 3                            |            |
| K8S\_PROBE\_INITIAL\_DELAY    | Seconds before health/ready checks starts           | 60                           |            |
| K8S\_PROBE\_PERIOD            | How long between probe checks                       | 10                           |            |
| K8S\_REPLICACOUNT             | Number of replicated Pods                           | 1                            |            |
| K8S\_REQUEST\_CPU             | Request at least this much CPU (ex. 1000m)          | 50m                          |            |
| K8S\_REQUEST\_RAM             | Request at least this much RAM (ex. 512Mi)          | 128Mi                        |            |
| K8S\_LIMIT\_CPU               | Limit max CPU (ex. 1000m)                           |                              |            |
| K8S\_LIMIT\_RAM               | Limit max RAM (ex. 512Mi)                           |                              |            |
| K8S\_SECRET\_PREFIX           | Application environment variable prefix             | K8S\_SECRET\_                |            |
| K8S\_TEMP\_STORAGE\_PATH      | Temporary volume mount storage path                 |                              |            |
| KOLGA\_DEBUG                  | Enable debug output                                 | False                        |            |
| KOLGA\_JOBS\_ONLY             | Run only job deployments                            | False                        |            |
| KUBECONFIG                    | Path to Kubernetes config                           |                              |            |
| MYSQL\_ENABLED                | Should a MySQL database be created for preview      | False                        |            |
| MYSQL\_VERSION\_TAG           | Version of MySQL for preview environment            | 5\.7                         |            |
| POSTGRES\_ENABLED             | Should a PostgreSQL database be created for preview | True                         |            |
| POSTGRES\_IMAGE               | PostgeSQL image for preview environment             | bitnami/postgresql:9.6       |            |
| PROJECT\_DIR                  | Path to where code is cloned and CI start path      |                              | GitLab     |
| PROJECT\_NAME                 | The name of the project                             |                              | GitLab     |
| PROJECT\_PATH\_SLUG           | Slug to project path \(<org>/<repo>\)               |                              | GitLab     |
| SERVICE\_PORT                 | Port that application listens on                    | 8000                         |            |


## Command variables

Certain variables reflect commands that will be run at certain stages of the applications
life-cycle. Such variables can for instance be used to run a command before the application
starts to do database migrations.

| Variable               | Description                    | Default | CI Support |
| ---------------------- | ------------------------------ | ------- | ---------- |
| APP_INITIALIZE_COMMAND | Command to run on first start  |         |            |
| APP_MIGRATE_COMMAND    | Command to run on every update |         |            |
