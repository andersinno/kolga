# Platforms

While the general actions taken by the DevOps pipeline is agnostic to the underlying
platform, there is still a need to support CI platforms native configurations.
Most CI platforms today have a stage setup, where jobs can be grouped together to
form a stage of jobs. For instance, the stage testing can include unit tests, e2e test
or style checking jobs.

The stages and jobs are named the same across all CI platforms as far as possible.

Note however that we do not put restrictions on the jobs or stages that are run and
new jobs and stages can be added and the default stages and jobs can be disabled.

**Supported platforms:**
* [GitLab](../../gitlab/index.md)
