#!/usr/bin/env bash

source utils/kubernetes_tools.sh
source utils/shell_utils.sh

if [[ -n "$@" ]]; then
    "$@"
else
    setup_kubernetes
    echo -e "\n#####################"
    echo "### Running tests ###"
    echo "#####################"
    pytest -ra -vvv --cov=scripts --cov-report xml --cov-report term
fi
