# Writing Dockerfiles

From Docker's Best practices for writing Dockerfiles:

> Docker builds images automatically by reading the instructions from a Dockerfile -- a
> text file that contains all commands, in order, needed to build a given image. A
> Dockerfile adheres to a specific format and set of instructions which you can find at
> Dockerfile reference.
>
> A Docker image consists of read-only layers each of which represents a Dockerfile
> instruction. The layers are stacked and each one is a delta of the changes from the
> previous layer.


## TL;DR

* Use the provided [base images][docker-hub].

* Keep the image slim.

* One service per image.

* Running the image should do everything that is necessary to bring up a working
  service.

* Use multi-stage builds, last stage should be the production build.

* Containers are run as root by default which is not nice. Drop root with
  `USER appuser`.

* Set owner when copying files: `COPY --chown=appuser:appuser`.

* Define an [entrypoint](#entrypoint).

[docker-hub]: https://hub.docker.com/u/andersinnovations


## Base image

We have production-ready base images for node, python, and node+python available at
[Docker Hub][docker-hub]. These images are based on debian and have

* a non-root user (`appuser`) for running the application,

* a directory for application code (`/app`),

* helpers for installing system packages (`apt-install.sh`, `apt-cleanup.sh`),

* `bash` as the shell, and

* `curl`, `git`, and [`wait-for-it.sh`][wait-for-it].

[wait-for-it]: https://github.com/vishnubob/wait-for-it 


## Entrypoint

The entrypoint that is defined in the `Dockerfile` gets run when the image is started
unless manually overridden by another entrypoint (`docker run
--entrypoint=<entrypoint>`).

By default -- when given no arguments -- the entrypoint should bring up a production
server (typically [uwsgi][] in Django's case) but in many projects some sort of
hot-reloading server is used for development purposes and sometimes it's useful to able
to run an altogether different command as well.

An example of an entrypoint script that handles all these cases and does some extra
setting-up when requested (very useful for local development):

```sh
#!/bin/bash

# Wait for database
if [[ "$WAIT_FOR_DATABASE" = "1" ]]; then
    wait-for-it.sh "${DATABASE_HOST}:${DATABASE_PORT-5432}"
fi

# Setup local development environment
if [[ "$APPLY_MIGRATIONS" = "1" ]]; then
    ./manage.py migrate --noinput
fi

if [[ ! -z "$@" ]]; then
    # Run the given command
    exec "$@"
elif [[ "$DEV_SERVER" = "1" ]]; then
    # Development server was requested
    exec ./manage.py runserver 0.0.0.0:8000
else
    # Always default to production environment
    exec uwsgi --ini .prod/uwsgi.ini
fi
```

[uwsgi]: https://uwsgi-docs.readthedocs.io/en/latest/


## On keeping it slim

* Do [multi-stage builds][multistage].

* Use `.dockerignore` (see [docs][dockerignore]) to exclude files from getting copied to
  the image. Usually it’s a good idea to exclude everything (`*`) and whitelist only the
  needed things (lines starting with `!`).

* Copy dependency files (`requirements.txt`, `package.json`, etc.)  first, install
  dependencies then copy the rest of the application code.

* Chain commands to do clean-up in the same layer.

* Note that removing files added in a previous layers does not make the image smaller.

[multistage]: https://docs.docker.com/develop/develop-images/multistage-build/
[dockerignore]: https://docs.docker.com/engine/reference/builder/#dockerignore-file


## Miscellaneous

### `appuser`

Containers are run as root by default. That’s usually not a good idea. You should switch
to a non-root user with `USER` instruction. The base images have user appuser (UID 1000)
and group appuser (GID 1000) for this purpose.

Use `COPY --chown=appuser:appuser ...` when copying files to the image. The reasoning
behind this is that if the files in the build context are not readable by others
(something like `chmod o-r` or a non-standard umask `077`) then `appuser` won't be able
to read the files as they will be owned by `root:root` after copying.


### Build arguments

The CI/CD pipeline has support for [build arguments][buildargs]. Environment variables
prefixed with `DOCKER_BUILD_ARG_` are passed to `docker image build` command.

[buildargs]: https://docs.docker.com/engine/reference/builder/#arg


### `.prod/`

Use `.prod/` for production specific files in your repository.


## See also

* Docker's [Best practices for writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
* Docker's [Use multi-stage builds](https://docs.docker.com/develop/develop-images/multistage-build/)
* [dive](https://github.com/wagoodman/dive): A tool for exploring each layer in a docker image
