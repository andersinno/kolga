# ===================================
FROM python:3.8-alpine AS base
# ===================================

# ===================================
FROM base AS build-base
# ===================================
RUN apk add --no-cache \
    python3 \
    python3-dev \
    curl

RUN ln -sf python3 /usr/bin/python
RUN ln -s pip3 /usr/bin/pip

# ===================================
FROM build-base AS kubectl
# ===================================
ARG KUBECTL_VERSION=1.17.2
ARG KUBECTL_CHECKSUM=7f9bc410e8cc7f3b4075b50ab144fe08fefc5e7a9d03b9c09ee2e7e483e0c436
ARG SOURCE=https://dl.k8s.io/v$KUBECTL_VERSION/kubernetes-client-linux-amd64.tar.gz
ARG TARGET=/kubernetes-client.tar.gz
RUN curl -fLSs "$SOURCE" -o "$TARGET"
RUN sha256sum "$TARGET"
RUN echo "$KUBECTL_CHECKSUM *$TARGET" | sha256sum -c -
RUN tar -xvf "$TARGET" -C /

# ===================================
FROM build-base AS helm
# ===================================
ARG HELM_VERSION=3.0.3
ARG HELM_CHECKSUM=fc75d62bafec2c3addc87b715ce2512820375ab812e6647dc724123b616586d6
ARG SOURCE=https://get.helm.sh/helm-v$HELM_VERSION-linux-amd64.tar.gz
ARG TARGET=/helm.tar.gz
RUN curl -fLSs "$SOURCE" -o "$TARGET"
RUN sha256sum "$TARGET"
RUN echo "$HELM_CHECKSUM *$TARGET" | sha256sum -c -
RUN mkdir -p /helm
RUN tar -xvf "$TARGET" -C /helm

# ===================================
FROM build-base AS poetry
# ===================================

ARG POETRY_CHECKSUM=89745d7cf34dc17f90b08600163b031b6fbfec5126ebce3d84444856d62a0224
ARG POETRY_TARGET=/tmp/get-poetry.py

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/1.0.0/get-poetry.py -o "$POETRY_TARGET"
RUN sha256sum "$POETRY_TARGET"
RUN echo "$POETRY_CHECKSUM *$POETRY_TARGET" | sha256sum -c -
RUN python /tmp/get-poetry.py

# Remove all other python version than the one used by the base image
# Note: `find` does not support negative lookahead, nor does `grep`
# Space savings: ~70MB
RUN find $HOME/.poetry/lib/poetry/_vendor \
      -type d \
      -not -regex "^.*py3.8.*$" \
      -not -path $HOME/.poetry/lib/poetry/_vendor \
      -exec rm -rf {} +

# ===================================
FROM build-base AS buildx
# ===================================

ARG BUILDX_CHECKSUM=30ea2f60b48e8a4a4b30e352e7116ef11d99bf60346668dd7c69619b85dae29a
ARG BUILDX_TARGET=/buildx/docker-buildx

RUN mkdir -p /buildx
RUN curl -fLSs https://github.com/docker/buildx/releases/download/v0.3.1/buildx-v0.3.1.linux-amd64 -o "$BUILDX_TARGET"
RUN sha256sum "$BUILDX_TARGET"
RUN echo "$BUILDX_CHECKSUM *$BUILDX_TARGET" | sha256sum -c -
RUN chmod a+x "$BUILDX_TARGET"

# ===================================
FROM build-base AS stage
# ===================================
WORKDIR /stage
ENV PATH=$PATH:/stage/usr/bin
COPY --from=kubectl /kubernetes/client/bin/kubectl ./usr/bin/
COPY --from=helm /helm/linux-amd64/helm ./usr/bin/
COPY --from=poetry /root/.poetry ./root/.poetry
COPY --from=buildx /buildx/docker-buildx ./usr/local/lib/docker/cli-plugins/

# ===================================
FROM docker:stable-dind as app-base
# ===================================

ENV PYTHONUNBUFFERED=1

COPY --from=stage /stage/ /

# Symlink poetry to bin
RUN ln -s $HOME/.poetry/bin/poetry /usr/bin/poetry

# Enable Buildx support
ENV DOCKER_CLI_EXPERIMENTAL=enabled

WORKDIR /app

COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml

RUN apk add --no-cache --virtual .build-deps \
        build-base \
        python3-dev \
    && apk add --no-cache --virtual .fetch-deps \
        curl \
    && apk add --no-cache \
        python3 \
        bash \
        sudo \
        nodejs \
        shadow \
        ca-certificates \
        git \
        make \
        openssl-dev \
        libffi-dev \
        apache2-utils \
    && ln -sf python3 /usr/bin/python \
    && ln -s pip3 /usr/bin/pip \
    && python3 -m ensurepip \
    && poetry config virtualenvs.create false \
	&& poetry install --no-dev --no-interaction \
	&& pip install docker-compose \
	&& apk del .build-deps \
	&& apk del .fetch-deps

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

# ===================================
FROM app-base AS development
# ===================================
LABEL "com.azure.dev.pipelines.agent.handler.node.path"="/usr/bin/node"
RUN apk add --no-cache --virtual .build-deps \
        build-base \
        python3-dev \
    && poetry install \
    && apk del .build-deps

COPY . /app

# ===================================
FROM app-base AS production
# ===================================
LABEL "com.azure.dev.pipelines.agent.handler.node.path"="/usr/bin/node"

COPY . /app
