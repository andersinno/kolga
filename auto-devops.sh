#!/bin/sh
# Auto DevOps variables and functions
[[ "$TRACE" ]] && set -x

# Database
auto_database_url=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${CI_ENVIRONMENT_SLUG}-postgres:5432/${POSTGRES_DB}
export DATABASE_URL=${DATABASE_URL-$auto_database_url}

export DOCKER_IMAGE_TAG_BASE=${CI_REGISTRY_IMAGE}/${DOCKER_IMAGE_NAME}
export DOCKER_IMAGE_TAG=:${DOCKER_IMAGE_TAG_BASE}:${CI_COMMIT_SHA}

function registry_login() {
  if [[ -n "$CI_REGISTRY_USER" ]]; then
    echo "Logging to GitLab Container Registry with CI credentials..."
    docker login -u "$CI_REGISTRY_USER" -p "$CI_REGISTRY_PASSWORD" "$CI_REGISTRY"
    echo ""
  fi
}

function fetch_submodules() {
  git submodule sync && git submodule update --init
}

function deploy_name() {
  name="$CI_ENVIRONMENT_SLUG"
  track="${1-stable}"

  if [[ "$track" != "stable" ]]; then
    name="$name-$track"
  fi

  echo $name
}

function application_secret_name() {
  track="${1-stable}"
  name=$(deploy_name "$track")

  echo "${name}-secret"
}

function test() {
  fetch_submodules
  registry_login

  docker pull $DOCKER_IMAGE_TAG
  export DOCKER_HOST='tcp://localhost:2375'
  export DOCKER_APP_IMAGE=$DOCKER_IMAGE_TAG
  export DOCKER_APP_COMMAND="make test-setup && make test'"
  make ci-command
}


# Extracts variables prefixed with K8S_SECRET_
# and creates a Kubernetes secret.
#
# e.g. If we have the following environment variables:
#   K8S_SECRET_A=value1
#   K8S_SECRET_B=multi\ word\ value
#
# Then we will create a secret with the following key-value pairs:
#   data:
#     A: dmFsdWUxCg==
#     B: bXVsdGkgd29yZCB2YWx1ZQo=
function create_application_secret() {
  track="${1-stable}"
  export APPLICATION_SECRET_NAME=$(application_secret_name "$track")

  bash -c '
    function k8s_prefixed_variables() {
      env | sed -n "s/^K8S_SECRET_\(.*\)$/\1/p"
    }

    kubectl create secret \
      -n "$KUBE_NAMESPACE" generic "$APPLICATION_SECRET_NAME" \
      --from-env-file <(k8s_prefixed_variables) -o yaml --dry-run |
      kubectl replace -n "$KUBE_NAMESPACE" --force -f -
  '
}

function kube_auth() {
  cluster="${1-production}"

  if [ "$cluster" = "qa" ]; then
    # TODO: TIX TYPO
    k8s_cluster="$K8S_QA_CLUSTER_NAME"
    k8s_token="$K8S_QA_TOKEN"
    k8s_api_url="$K8S_QA_API_URL"
  fi

  echo "$K8S_QA_CERTIFICATE" > ca.crt
  kubectl config set-cluster "$k8s_cluster" --server "$k8s_api_url" --certificate-authority=ca.crt
  kubectl config set-credentials "$k8s_cluster" --token="$k8s_token"
  kubectl config set-context "$k8s_cluster" --user="$k8s_cluster" --cluster="$k8s_cluster" --namespace="$KUBE_NAMESPACE"
  kubectl config use-context "$k8s_cluster"
}

function ensure_namespace() {
  kubectl describe namespace "$KUBE_NAMESPACE" || (kubectl create namespace "$KUBE_NAMESPACE" && kubectl label namespace $KUBE_NAMESPACE app=kubed)
  kubectl label namespace $KUBE_NAMESPACE app=kubed --overwrite
}

# Make sure that Helm repos are set up
function setup_helm() {
  echo "Setting up Helm"
  helm init --client-only
  helm repo update
}

# Deploys a database for the application
function initialize_database() {
  track="${1-stable}"
  name=$(deploy_name "$track")

  if [[ "$POSTGRES_ENABLED" -eq 1 ]]; then
    echo "Settings up database"
    helm fetch stable/postgresql --version 3.10.1 --untar --untardir ./database/helm
    mkdir -p ./database/manifests
    helm template database/helm/postgresql \
      --name "$name" \
      --namespace "$KUBE_NAMESPACE" \
      --set image.tag="$POSTGRES_VERSION_TAG" \
      --set postgresqlUsername="$POSTGRES_USER" \
      --set postgresqlPassword="$POSTGRES_PASSWORD" \
      --set postgresqlDatabase="$POSTGRES_DB" \
      --set nameOverride="postgres" \
      --output-dir ./database/manifests

    # --force is a destructive and disruptive action and will cause the service to be recreated and
    #         and will cause downtime. We don't mind in this case we do _want_ to recreate everything.
    kubectl replace --recursive -f ./database/manifests/postgresql --force
    sleep 5
    kubectl wait pod --for=condition=ready --timeout=600s -l app=postgres,release=${CI_ENVIRONMENT_SLUG}
  fi
}

function deploy() {
  track="${1-stable}"
  name=$(deploy_name "$track")

  setup_helm

  create_application_secret

  initialize_database "$track"
  mkdir ./manifests
  helm template ./helm \
    --name "$name" \
    --set namespace="$KUBE_NAMESPACE" \
    --set image="$DOCKER_IMAGE_TAG" \
    --set appName="$CI_ENVIRONMENT_SLUG" \
    --set application.track="$track" \
    --set application.database_url="$DATABASE_URL" \
    --set application.secretName="$APPLICATION_SECRET_NAME" \
    --set application.initializeCommand="$DB_INITIALIZE" \
    --set application.migrateCommand="$DB_MIGRATE" \
    --set service.url="$CI_ENVIRONMENT_URL" \
    --output-dir ./manifests

  # [Re-] Running jobs by first removing them and then applying them again
  if [[ -n "$DB_INITIALIZE" ]]; then
    echo "Applying initialization command..."
    kubectl delete --ignore-not-found jobs/${CI_ENVIRONMENT_SLUG}-initialize
    kubectl apply -f ./manifests/anders-deploy-app/templates/00-init-job.yaml
    kubectl wait --for=condition=complete --timeout=600s jobs/${CI_ENVIRONMENT_SLUG}-initialize

    rm ./manifests/anders-deploy-app/templates/00-init-job.yaml
  fi

  if [[ -n "$DB_MIGRATE" ]]; then
    echo "Applying migration command..."
    kubectl delete --ignore-not-found jobs/${CI_ENVIRONMENT_SLUG}-migrate
    kubectl apply -f ./manifests/anders-deploy-app/templates/01-migrate-job.yaml
    kubectl wait --for=condition=complete --timeout=600s jobs/${CI_ENVIRONMENT_SLUG}-migrate

    rm ./manifests/anders-deploy-app/templates/01-migrate-job.yaml
  fi

  kubectl apply --recursive -f ./manifests/anders-deploy-app/templates
  kubectl wait --for=condition=available --timeout=600s deployments/${CI_ENVIRONMENT_SLUG}
}

function setup_test_db() {
  if [ -z ${KUBERNETES_PORT+x} ]; then
    DB_HOST=postgres
  else
    DB_HOST=localhost
  fi
  export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DB_HOST}:5432/${POSTGRES_DB}"
}

function build() {
  fetch_submodules

  registry_login
  if ! docker pull ${DOCKER_IMAGE_TAG_BASE}:master > /dev/null; then
    echo "Pulling latest master image for the project failed, running without cache"
  fi
  if ! docker pull ${CI_REGISTRY_IMAGE}:${CI_COMMIT_REF_NAME} > /dev/null; then
    echo "Pulling branch specific docker cache failed, building without"
  fi

  docker build \
    --cache-from ${DOCKER_IMAGE_TAG_BASE}:master \
    --cache-from ${DOCKER_IMAGE_TAG_BASE}:${CI_COMMIT_REF_NAME} \
    -t ${DOCKER_IMAGE_TAG} \
    -t ${DOCKER_IMAGE_TAG_BASE}:${CI_COMMIT_REF_NAME} \
    -f Dockerfile .

  echo "Pushing to GitLab Container Registry..."
  docker push ${DOCKER_IMAGE_TAG}
  docker push ${DOCKER_IMAGE_TAG_BASE}:${CI_COMMIT_REF_NAME}
  echo ""
}

function delete() {
  track="${1-stable}"
  name=$(deploy_name "$track")

  kubectl delete \
    pods,services,jobs,deployments,statefulsets,configmap,serviceaccount,rolebinding,role \
    -l release="$name" \
    -n "$KUBE_NAMESPACE" \
    --include-uninitialized

  secret_name=$(application_secret_name "$track")
  kubectl delete secret --ignore-not-found -n "$KUBE_NAMESPACE" "$secret_name"
}
