# GitLab CI/CD

- The CI-pipeline uses GitLab's [CI/CD pipelines](https://about.gitlab.com/product/continuous-integration/). Projects not hosted on GitLab must be set up to use GitLab as CI/CD tool.
    - This setup is done by adding a new project in GitLab and selecting CI/CD for external repo
- Some configuration is required for the GitLab project to enable all the features in the CI/CD pipeline.
    - The configuration is done using the Terraform tool
- The project should be Dockerized i.e. it must produce a production-ready application container.
    - The containers must be able to run without any command given to them by default
    - The containers must not assume that other required services are up and running before it, and must, therefore, wait for required services
    - The pipeline runs the container as is on Kubernetes.
- The pipeline provides three environments:
    - A review environment is created for every pull/merge request and re-created when PR/MR is updated.
      Depending on the config, the pipeline builds, tests and runs the app. It then provides access to the running
      application using a dynamically created URL. The review environment starts a database instance
      (Postgres by default) in the same network as the application.
        - The database URL can be accessed through the exposed DATABASE_URLenvironment variable
    - A staging environment is created from one selected repository branch - usually master or develop branch and is accessible using a static URL. The staging environment uses a PostgreSQL database provided by [https://aiven.io/](https://aiven.io/). The database contents are static and not re-created when the application is re-built.
- The application should be configurable using environmental variables (instead of config files) as the CI-pipeline provides an easy way of injecting variables into the built app.
- CI-pipeline is configured using .gitlab-ci.yml placed at the root directory of the project. [A ci-configuration repo](https://gitlab.com/City-of-Helsinki/KuVa/ci-cd-config/ci-configuration) provides ready-made functions for running the CI-pipeline, and the user can configure only the desired pipeline steps if needed.


## Configuration variables

The application should be configurable using environmental variables rather than using configuration files.
The CI-pipeline provides a method to inject environmental variables into started applications.
All variables with prefix K8S_SECRET_ will be available for the running application.
The prefix will be stripped before the application sees the variable. i.e. K8S_SECRET_DEBUG = "1" will become DEBUG = "1".

### Default variables

Read more about the variables that are available for each of the stages in the **STAGES** docs.

## Stages

The configurations listed below are the default pipeline configurations for each steps of the pipeline.
All of the steps are fully configurable and optional. 

There are two ways to configure a projects pipeline. Either use a default setup which enables everything
except the build stage in the pipeline and then disable certain steps by environment variables,
or use a base template that does not run anything without being extended.

The CI-pipeline is enabled by placing a configuration file in the root of the project repository.
The only mandatory part in the config file is including the base template from the ci-configuration project as shown in the example below. Users can then optionally enable the building stage (which is mandatory if any other stages are enabled), the review stage and the staging stage.

    include:
      - project: '<path_to_config>'
        ref: v1
        file: '/.gitlab-ci-template.yml'

To use a base template that does not run any jobs by default and required that all the user extends each stage manually, include the following instead.

    include:
      - project: '<path_to_config>'
        ref: v1
        file: '/.gitlab-ci-base-template.yml'

### Build

The build stage produces container images and stores them in a docker registry for other stages to consume. For more information about customizing the build process

    .build:
      services:
        - docker:stable-dind
      variables:
        DOCKER_BUILD_SOURCE: Dockerfile
      stage: build
      script:
        - devops create_images
      only:
        - merge_requests
        - master
        - qa
      except:
        variables:
          - $BUILD_DISABLED

### Test

    .test:
      services:
        - docker:stable-dind
      stage: test
      script:
        - set_env_from_devops docker_test_image BUILT_DOCKER_TEST_IMAGE
        - devops test_setup
        - make test
      only:
        - merge_requests
        - master
        - qa
      except:
        variables:
          - $TEST_DISABLED

Note that Docker and Docker compose is available in the image that your test stage is running. This means that if you want to run tests on the images that were previously build, this can be done by either running the Docker image with `docker run $DOCKER_TEST_IMAGE_STAGE <command>` or use `$DOCKER_TEST_IMAGE_STAGE`  in your Docker compose file. Note that to set your Docker compose file to be usable both in CI testing and for local development, a configuration such as this can be used.

    app:
        image: ${BUILT_DOCKER_TEST_IMAGE:-none}
        build:
          context: .
          target: development

For running tests without using `make test` you can override the scripts part of the job like this:

    test-codeanalysis:
      extends: .test
      only:
        refs:
          - develop # Runs test only on the _develop_ branch
      variables:
        DEBUG: 1
      script:
        - flake8
        - py.test -ra -vvv --cov
        - isort -c

### Review

Review stage or development stage is meant to be triggered by pull requests (PR) and by changes to PRs. The environment provides an ephemeral database instance that is re-created between the runs. The database URL is stored in an environmental variable DATABASE_URL. Review stages will get a dynamically created URL for accessing the running application. It will be provided a certificate from Let's encrypts staging environment.

    .review:
      stage: review
      script:
        - devops deploy_application --track review
      environment:
        name: qa/r/${CI_COMMIT_REF_SLUG}
        url: http://$CI_PROJECT_PATH_SLUG-$CI_ENVIRONMENT_SLUG.$K8S_QA_INGRESS_DOMAIN
        on_stop: stop_review
      variables:
        TRACK: review
      only:
        refs:
          - merge_requests
        kubernetes: active
      except:
        refs:
          - master
        variables:
          - $REVIEW_DISABLED

### QA/Staging

The staging stage is meant to be triggered by pushes to the project's master-branch. There will always be only one staging environment per project. The environment provides a permanent database storage that is not cleaned between runs. The database URL is stored in an environmental variable DATABASE_URL. The Staging stages will have a static URL and the certificate is provided by Let's Encrypt.

    .staging:
      stage: staging
      script:
        - devops deploy_application --track staging
      environment:
        name: qa/staging
        url: http://$CI_PROJECT_PATH_SLUG-qa.$K8S_QA_INGRESS_DOMAIN
      only:
        refs:
          - master
        kubernetes: active
      except:
        variables:
          - $STAGING_DISABLED
