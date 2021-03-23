# ===================================
FROM python:3.8.8-alpine3.13 AS build-base
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
ARG KUBECTL_VERSION=1.17.17
ARG KUBECTL_CHECKSUM=f4eb3da33d74b792f0833332fb509f1443c6f89c32acf8d79cadf6108da34d0f
ARG SOURCE=https://dl.k8s.io/v$KUBECTL_VERSION/kubernetes-client-linux-amd64.tar.gz
ARG TARGET=/kubernetes-client.tar.gz
RUN curl -fLSs "$SOURCE" -o "$TARGET"
RUN echo "$KUBECTL_CHECKSUM *$TARGET" | sha256sum -c -
RUN tar -xvf "$TARGET" -C /

# ===================================
FROM build-base AS helm
# ===================================
ARG HELM_VERSION=3.5.3
ARG HELM_CHECKSUM=2170a1a644a9e0b863f00c17b761ce33d4323da64fc74562a3a6df2abbf6cd70
ARG SOURCE=https://get.helm.sh/helm-v$HELM_VERSION-linux-amd64.tar.gz
ARG TARGET=/helm.tar.gz
RUN curl -fLSs "$SOURCE" -o "$TARGET"
RUN echo "$HELM_CHECKSUM *$TARGET" | sha256sum -c -
RUN mkdir -p /helm
RUN tar -xvf "$TARGET" -C /helm

# ===================================
FROM build-base AS poetry
# ===================================
ARG POETRY_CHECKSUM=e973b3badb95a916bfe250c22eeb7253130fd87312afa326eb02b8bdcea8f4a7
ARG POETRY_TARGET=/tmp/get-poetry.py

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/1.1.5/get-poetry.py -o "$POETRY_TARGET"
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

ARG BUILDX_CHECKSUM=5f1dda3ae598e82c3186c2766506921e6f9f51c93b5ba43f7b42b659db4aa48d
ARG BUILDX_TARGET=/buildx/docker-buildx

RUN mkdir -p /buildx
RUN curl -fLSs https://github.com/docker/buildx/releases/download/v0.5.1/buildx-v0.5.1.linux-amd64 -o "$BUILDX_TARGET"
RUN echo "$BUILDX_CHECKSUM *$BUILDX_TARGET" | sha256sum -c -
RUN chmod a+x "$BUILDX_TARGET"

# ===================================
FROM build-base AS tools
# ===================================
WORKDIR /tools
ENV PATH=$PATH:/tools/usr/bin
COPY --from=kubectl /kubernetes/client/bin/kubectl ./usr/bin/
COPY --from=helm /helm/linux-amd64/helm ./usr/bin/
COPY --from=poetry /root/.poetry ./root/.poetry
COPY --from=buildx /buildx/docker-buildx ./usr/local/lib/docker/cli-plugins/

# ===================================
FROM docker:20.10.5-dind as app-base
# ===================================

ENV PYTHONUNBUFFERED=1

COPY --from=tools /tools/ /

# Symlink poetry to bin
RUN ln -s $HOME/.poetry/bin/poetry /usr/bin/poetry

# Enable Buildx support
ENV DOCKER_CLI_EXPERIMENTAL=enabled

WORKDIR /app

COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml

RUN apk add --no-cache --virtual .build-deps \
        build-base \
        cargo \
        python3-dev \
        rust \
    && apk add --no-cache \
        apache2-utils \
        bash \
        ca-certificates \
        git \
        libffi-dev \
        make \
        nodejs \
        openssl-dev \
        python3 \
        shadow \
    && ln -sf python3 /usr/bin/python \
    && ln -s pip3 /usr/bin/pip \
    && python3 -m ensurepip \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction \
    && pip install docker-compose \
    && apk del .build-deps

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
