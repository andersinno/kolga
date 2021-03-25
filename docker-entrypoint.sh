#!/usr/bin/env bash

set -e
set -u

source ./utils/test_utils.sh

if [ $# -eq 0 ]; then
    # Run tests with Docker and Kubernetes by default.
    set -- --with-docker --with-k8s
fi

while [ $# -gt 0 ]; do
    case "$1" in
    --with-docker)
        check_docker || echo "Warning: cannot connect to Docker"
        shift;;
    --with-k8s)
        setup_kubernetes
        shift;;
    *)
        break;;
    esac
done

if [ $# -eq 0 ]; then
    echo
    echo "#####################"
    echo "### Running tests ###"
    echo "#####################"
    set -- pytest -ra -vvv --cov=. --cov-report xml --cov-report term --junit-xml=pytest.xml
fi

echo "+ $@"
exec "$@"
