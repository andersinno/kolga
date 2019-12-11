#!/usr/bin/env bash


function setup_kubernetes() {
    echo -e "\n#############################"
    echo "### Setting up Kubernetes ###"
    echo "#############################"
    until nc -z -v -w30 kubernetes 6443
    do
        echo "Waiting for Kubernetes cluster to respond"
        sleep 1
    done

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
