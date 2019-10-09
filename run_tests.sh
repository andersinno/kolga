#!/usr/bin/env bash

docker-compose down -v
docker-compose up -V --abort-on-container-exit --exit-code-from client "$@"
