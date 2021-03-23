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
ARG HELM_VERSION=3.5.2
ARG HELM_CHECKSUM=01b317c506f8b6ad60b11b1dc3f093276bb703281cb1ae01132752253ec706a2
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

ARG POETRY_CHECKSUM=e973b3badb95a916bfe250c22eeb7253130fd87312afa326eb02b8bdcea8f4a7
ARG POETRY_TARGET=/tmp/get-poetry.py

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/1.1.2/get-poetry.py -o "$POETRY_TARGET"
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

ARG BUILDX_CHECKSUM=c21f07356de93a4fa5d1b7998252ea5f518dbe94ae781e0edeec7d7e29fdf899
ARG BUILDX_TARGET=/buildx/docker-buildx

RUN mkdir -p /buildx
RUN curl -fLSs https://github.com/docker/buildx/releases/download/v0.4.2/buildx-v0.4.2.linux-amd64 -o "$BUILDX_TARGET"
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
FROM docker:20.10.5-dind as app-base
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

ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

RUN apk add --no-cache --virtual .build-deps \
        build-base \
        python3-dev \
    && apk add --no-cache --virtual .fetch-deps \
        curl \
    && apk add --no-cache \
        python3 \
        bash \
        nodejs \
        shadow \
        ca-certificates \
        git \
        make \
        openssl-dev \
        libffi-dev \
        apache2-utils \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal \
    && chmod -R a+w $RUSTUP_HOME $CARGO_HOME \
    && ln -sf python3 /usr/bin/python \
    && ln -s pip3 /usr/bin/pip \
    && python3 -m ensurepip \
    && poetry config virtualenvs.create false \
	&& poetry install --no-dev --no-interaction \
	&& pip install docker-compose \
	&& apk del .build-deps \
	&& apk del .fetch-deps \
    && rustup self uninstall -y

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
