#!/bin/sh

set -e
set -u

# Set DOCKER_SOCKET_PATH if not set
DOCKER_SOCKET_PATH=${DOCKER_SOCKET_PATH:-/var/run/docker.sock}
USERID=$(id -u)

if [ "${1-}" = "--as-root" ]; then
    shift
elif [ "$USERID" != "0" ]; then
    # Get GID from Docker daemon's socket
    export GROUPID=$(stat -c %g "$DOCKER_SOCKET_PATH")
    # Use current user's UID
    export USERID
    # Ensure that docker-compose uses the same socket path
    export DOCKER_SOCKET_PATH
fi

docker-compose down -v
docker-compose up -V --abort-on-container-exit --exit-code-from client "$@"
