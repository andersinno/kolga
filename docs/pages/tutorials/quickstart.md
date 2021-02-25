# Quick-start Guide

## Preparing your application

- Write a Dockerfile for your project

- Add liveness and readiness probes: `/healthz` and `/readiness` should
  respond with `200 OK` when the application is ready to serve requests

- Make sure everything that needs to be configured can be configured with
  environment variables. For example:
    - Database URL,
    - Media file storage, S3-combatible object storage in testing and
      production,
    - Outgoing mail SMTP server.

- Add secrets to CI/CD environment variables starting with `K8S_SECRET_`

- Make sure the application listens on port 8000 or set `SERVICE_PORT`
  variable


## GitLab

- Import the CI config for your CI/CD pipeline, for GitLab for example:
```yaml
include:
  - project: 'anders/ci-configuration'
    ref: v3
    file: '/.gitlab-ci-template.yml'
```

- Define a build job
```yaml
build:
  extends: .build
```

- Add URL for the staging environment
```yaml
staging:
  environment:
    url: http://<your_staging_subdomain>.$K8S_QA_INGRESS_DOMAIN
  only:
    - master
```
