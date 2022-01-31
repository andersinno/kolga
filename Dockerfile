# ===================================
FROM python:3.9.10-alpine3.15 AS build-base
# ===================================

# ===================================
FROM build-base AS kubectl
# ===================================
ARG KUBECTL_VERSION=1.19.16
ARG KUBECTL_CHECKSUM=9524a026af932ac9ca1895563060f7fb3b89f1387016e69a1a73cf7ce0f9baa54775b00c886557a97bae9b6dbc1b49c045da5dcea9ca2c1452c18c5c45fefd55
ARG TARGET=/kubernetes-client.tar.gz

ADD https://dl.k8s.io/v${KUBECTL_VERSION}/kubernetes-client-linux-amd64.tar.gz "$TARGET"
RUN set -eux; \
    echo "$KUBECTL_CHECKSUM *$TARGET" | sha512sum -c -; \
    tar -xvf "$TARGET" -C /

# ===================================
FROM build-base AS helm
# ===================================
ARG HELM_VERSION=3.7.1
ARG HELM_CHECKSUM=6cd6cad4b97e10c33c978ff3ac97bb42b68f79766f1d2284cfd62ec04cd177f4
ARG TARGET=/helm.tar.gz

ADD https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz "$TARGET"
RUN set -eux; \
    echo "$HELM_CHECKSUM *$TARGET" | sha256sum -c -; \
    mkdir -p /helm; \
    tar -xvf "$TARGET" -C /helm

# ===================================
FROM build-base AS poetry
# ===================================
ARG POETRY_VERSION=1.1.11
ARG POETRY_CHECKSUM=e973b3badb95a916bfe250c22eeb7253130fd87312afa326eb02b8bdcea8f4a7
ARG TARGET=/tmp/get-poetry.py

ADD https://raw.githubusercontent.com/python-poetry/poetry/${POETRY_VERSION}/get-poetry.py "$TARGET"
RUN set -eux; \
    echo "$POETRY_CHECKSUM *$TARGET" | sha256sum -c -; \
    python /tmp/get-poetry.py --version "${POETRY_VERSION}"; \
    # Remove all other python version than the one used by the base image \
    # Note: `find` does not support negative lookahead, nor does `grep` \
    # Space savings: ~70MB \
    find $HOME/.poetry/lib/poetry/_vendor \
        -type d \
        -not -regex "^.*py${PYTHON_VERSION%.*}.*$" \
        -not -path $HOME/.poetry/lib/poetry/_vendor \
        -exec rm -rf {} +;

# ===================================
FROM poetry AS requirements-txt
# ===================================
COPY poetry.lock pyproject.toml /
RUN set -eux; \
    ln -s $HOME/.poetry/bin/poetry /usr/bin/poetry; \
    poetry export --no-ansi --no-interaction -o /requirements.txt

# ===================================
FROM build-base AS buildx
# ===================================
ARG BUILDX_VERSION=0.7.1
ARG BUILDX_CHECKSUM=22fcb78c66905bf6ddf198118aaa9838b0349a25347606264be17e4276d6d5fc
ARG TARGET=/buildx/docker-buildx

ADD https://github.com/docker/buildx/releases/download/v${BUILDX_VERSION}/buildx-v${BUILDX_VERSION}.linux-amd64 "$TARGET"
RUN set -eux; \
    echo "$BUILDX_CHECKSUM *$TARGET" | sha256sum -c -; \
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

COPY --from=requirements-txt /requirements.txt /tmp/requirements.txt

RUN apk add --no-cache --virtual .build-deps \
        build-base \
        cargo \
        libffi-dev \
        openssl-dev \
        python3-dev \
        rust \
    && apk add --no-cache \
        apache2-utils \
        bash \
        ca-certificates \
        docker-cli \
        git \
        libffi \
        make \
        nodejs \
        openssl \
        python3 \
        shadow \
    && ln -sf python3 /usr/bin/python \
    && ln -s pip3 /usr/bin/pip \
    && python3 -m ensurepip \
    && pip install --no-cache-dir --no-input -r /tmp/requirements.txt \
    && pip install --no-cache-dir --no-input docker-compose \
    && rm -rf /root/.cache \
    && rm -rf /root/.cargo \
    && apk del .build-deps

# ===================================
FROM app-base AS development
# ===================================
LABEL "com.azure.dev.pipelines.agent.handler.node.path"="/usr/bin/node"

# Create a writable directory for shared configurations
RUN mkdir -m777 /config

COPY --from=poetry /root/.poetry /root/.poetry
RUN ln -s /root/.poetry/bin/poetry /usr/bin/poetry

COPY poetry.lock pyproject.toml /app/
RUN apk add --no-cache --virtual .build-deps \
        build-base \
        python3-dev \
    && poetry config virtualenvs.create false \
    && poetry install \
    && rm -r /root/.cache \
    && apk del .build-deps

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
