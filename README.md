# Anders CI/CD DevOps

> Version 3 is still in BETA and is therefor in a volatile state and can change without notice

CI/CD configuration for running a complete DevOps pipeline with all stages
from Docker builds and testnig to review, QA/staging and production environment
creation.

## Contents
* [Stages](pages/stages.md)
* [Variables](pages/variables.md)
* [Platforms](pages/platforms/index.md)
* [Libs](pages/libs/index.md)

## TL;DR
- Write a Dockerfile for your project

- Add liveness and readiness probes: `/healthz` and `/readiness` should
  respond with `200 OK` when the application is ready to serve requests

- Make sure everything that needs to be configured can be configured with a
  environment variable. For example:
    - Database URL
    - Media file storage, S3-combatible object storage in testing and
      production

- Add secrets to CI/CD environment variables starting with `K8S_SECRET_`

- Make sure the application listens on port 8000 or set `SERVICE_PORT`

- Import the CI config for your CI/CD pipeline, for GitLab for example:
```yaml
include:
  - project: 'anders/ci-configuration'
    ref: v2
    file: '/.gitlab-ci-template.yml'
```

- Add URL for the staging environment
```yaml
staging:
  environment:
    url: http://<your_staging_subdomain>.$K8S_QA_INGRESS_DOMAIN
  only:
    - master
```
