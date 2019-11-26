#!/usr/bin/env bash

function set_env_from_devops() {
    if [ "$#" -ne 2 ]; then
        echo "Usage: set_env_from_devops <devops command> <environment variable name>"
        exit 1
    fi

    exported_value=$2="$(./devops "$1")"
    export "$exported_value"
}
