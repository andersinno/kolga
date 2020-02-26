#!/usr/bin/env bash

export DOCKER_SOCKET_PATH=/var/run/docker.sock

if [ "$1" != "--as-root" ]; then
    # Get GID from Docker daemon's socket
    export GROUPID=$(stat -c %g "$DOCKER_SOCKET_PATH")
    # Use current user's UID
    export USERID=$(id -u)
fi

docker-compose down -v
docker-compose up -V --abort-on-container-exit --exit-code-from client "$@"
