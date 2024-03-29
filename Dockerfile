# ===================================
FROM python:3.11-alpine AS build-base
# ===================================

# ===================================
FROM build-base AS kubectl
# ===================================
ARG KUBECTL_VERSION=1.27.7
ARG KUBECTL_CHECKSUM=87b7ac839cac8d96efa1c6170cf32ed2bbe14e7194971df4b4736699152e294a0aa0018f3d8ae1dcf9905c3c784a7a15c297382450c0431a0daf98f300d3ef16
ARG TARGET=/kubernetes-client.tar.gz

ADD https://dl.k8s.io/v${KUBECTL_VERSION}/kubernetes-client-linux-amd64.tar.gz "$TARGET"
RUN set -eux; \
    echo "$KUBECTL_CHECKSUM *$TARGET" | sha512sum -c -; \
    tar -xvf "$TARGET" -C /

# ===================================
FROM build-base AS helm
# ===================================
ARG HELM_VERSION=3.13.2
ARG HELM_CHECKSUM=55a8e6dce87a1e52c61e0ce7a89bf85b38725ba3e8deb51d4a08ade8a2c70b2d
ARG TARGET=/helm.tar.gz

ADD https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz "$TARGET"
RUN set -eux; \
    echo "$HELM_CHECKSUM *$TARGET" | sha256sum -c -; \
    mkdir -p /helm; \
    tar -xvf "$TARGET" -C /helm

# ===================================
FROM build-base AS requirements-txt
# ===================================
RUN pip install poetry poetry-plugin-export
COPY poetry.lock pyproject.toml /
RUN poetry export \
        --no-ansi \
        --no-interaction \
        --extras opentelemetry \
        --output /requirements.txt
RUN poetry export \
        --no-ansi \
        --no-interaction \
        --only dev \
        --output /requirements-dev.txt

# ===================================
FROM build-base AS buildx
# ===================================
ARG BUILDX_VERSION=0.11.2
ARG BUILDX_CHECKSUM=60569a65eb08e28eadcd9e9ff82a1f4166ed2867af48c1ec1b7b82d3ca15ec29d9972186cd7b84178dadc050f66e59f138d5e391f47dd17ac474e5aee789fc47
ARG TARGET=/buildx/docker-buildx

ADD https://github.com/docker/buildx/releases/download/v${BUILDX_VERSION}/buildx-v${BUILDX_VERSION}.linux-amd64 "$TARGET"
RUN set -eux; \
    echo "$BUILDX_CHECKSUM *$TARGET" | sha512sum -c -; \
    chmod a+x "$TARGET"

# ===================================
FROM build-base AS tools
# ===================================
WORKDIR /tools
COPY --from=kubectl /kubernetes/client/bin/kubectl ./usr/bin/
COPY --from=helm /helm/linux-amd64/helm ./usr/bin/
COPY --from=buildx /buildx/docker-buildx ./usr/local/lib/docker/cli-plugins/

# ===================================
FROM build-base AS app-base
# ===================================
COPY --from=tools /tools/ /

# Enable Buildx support
ENV DOCKER_CLI_EXPERIMENTAL=enabled

WORKDIR /app

# Add a wrapper for docker that waits for docker daemon. See:
# https://gitlab.com/gitlab-org/gitlab-runner/-/issues/27300
COPY ./utils/docker-wrapper.sh /usr/local/bin/docker
RUN chmod a+x /usr/local/bin/docker

RUN apk add --no-cache \
        apache2-utils \
        bash \
        ca-certificates \
        docker-cli \
        docker-cli-compose \
        git \
        libffi \
        make \
        nodejs \
        openssl \
        python3 \
        shadow \
    && ln -sf python3 /usr/bin/python \
    && ln -s pip3 /usr/bin/pip \
    && python3 -m ensurepip

COPY --from=requirements-txt /requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-input -r /tmp/requirements.txt \
    && rm -rf /root/.cache /root/.cargo

# ===================================
FROM app-base AS development
# ===================================
LABEL "com.azure.dev.pipelines.agent.handler.node.path"="/usr/bin/node"

# Create a writable directory for shared configurations
RUN mkdir -m777 /config

COPY --from=requirements-txt /requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir --no-input -r /tmp/requirements-dev.txt \
    && rm -rf /root/.cache /root/.cargo

COPY . /app

RUN chmod 755 /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# ===================================
FROM app-base AS production
# ===================================
LABEL "com.azure.dev.pipelines.agent.handler.node.path"="/usr/bin/node"

COPY ./helm /app/helm
COPY ./devops /app/
COPY ./kolga /app/kolga
