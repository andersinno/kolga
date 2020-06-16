set_docker_host() {
    if [ -z "$DOCKER_HOST" ]; then
        if [ ! -z "$KUBERNETES_PORT" ]; then
            export DOCKER_HOST=tcp://localhost:2375
        else
            export DOCKER_HOST=http://docker:2375
        fi
    fi
}

set_env_from_devops() {
    if [ "$#" -ne 2 ]; then
        echo "Usage: set_env_from_devops <devops command> <environment variable name>"
        exit 1
    fi

    exported_value=$2="$(devops "$1")"
    export "$exported_value"
}

setup_buildkit() {
    if docker buildx &>/dev/null; then
        printf "🐳 Setting up buildx environment: "
        docker buildx create --name kolgabk --use > /dev/null
        mkdir -p /tmp/buildx/cache
        printf "kolgabk\n"
    fi
}
