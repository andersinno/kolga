check_docker() {
    echo
    echo "###########################"
    echo "### Checking for Docker ###"
    echo "###########################"

    if [ -z "$CONTAINER_REGISTRY" ]; then
	return 1
    fi

    local HOST=${CONTAINER_REGISTRY//:*}
    local PORT=${CONTAINER_REGISTRY##*:}

    wait_for_tcp "$HOST" "$PORT"
    export TEST_DOCKER_ACTIVE=1
}

setup_kubernetes() {
    echo
    echo "#############################"
    echo "### Setting up Kubernetes ###"
    echo "#############################"

    wait_for_tcp kubernetes 6443

    # Give some time for the service to create the required config files
    sleep 10

    # This is the same way that K3S modifies their kubeconfig
    # for e2e testing accoring to this file:
    # https://github.com/rancher/k3s/blob/d6c5f6b99598c8e59795d2ceb6c19c8cdc8d73c7/e2e/run-test.sh
    sed -i 's/127.0.0.1/kubernetes/g' $KUBECONFIG

    if [[ "$(kubectl cluster-info)" == *"Kubernetes master"*"https://kubernetes:6443"* ]]; then
        export TEST_CLUSTER_ACTIVE=1
        echo "Using kubernetes cluster on https://kubernetes:6443"
    fi

    echo "Settings up local storage for nodes"
    kubectl apply -f tests/manifests/local-path-storage.yaml
}

wait_for_tcp() {
    HOST=$1
    PORT=$2
    N_RETRIES=${3-90}

    echo "Waiting for $HOST:$PORT..."
    until [ $N_RETRIES -lt 1 ]; do
	nc -z -w15 "$HOST" "$PORT" 2>/dev/null && return
	sleep 1
	(( N_RETRIES-- ))
    done

    echo "FAILED to connect $HOST:$PORT!"
    false
}
