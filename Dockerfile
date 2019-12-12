# ===================================
FROM python:3.7-alpine AS base
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
ARG KUBECTL_VERSION=1.16.4
ARG KUBECTL_CHECKSUM=407444fcbfa6905d96e3584fd1f008d1d844108763fe45e2f30f58efea661501
ARG SOURCE=https://dl.k8s.io/v$KUBECTL_VERSION/kubernetes-client-linux-amd64.tar.gz
ARG TARGET=/kubernetes-client.tar.gz
RUN curl -fLSs "$SOURCE" -o "$TARGET"
RUN sha256sum "$TARGET"
RUN echo "$KUBECTL_CHECKSUM *$TARGET" | sha256sum -c -
RUN tar -xvf "$TARGET" -C /

# ===================================
FROM build-base AS helm
# ===================================
ARG HELM_VERSION=3.0.1
ARG HELM_CHECKSUM=6de3337bb7683fd62f915d156cfc13c1cf73dc183bd39f2fb4644498c7595805
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

ARG POETRY_CHECKSUM=3e569de8856be25f4a06bd43c72d3a876a8e3f148f088b151b5770ddeaae611e
ARG POETRY_TARGET=/tmp/get-poetry.py

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/1.0.0b5/get-poetry.py -o "$POETRY_TARGET"
RUN sha256sum "$POETRY_TARGET"
RUN echo "$POETRY_CHECKSUM *$POETRY_TARGET" | sha256sum -c -
RUN python /tmp/get-poetry.py

# ===================================
FROM build-base AS stage
# ===================================
WORKDIR /stage
ENV PATH=$PATH:/stage/usr/bin
COPY --from=kubectl /kubernetes/client/bin/kubectl ./usr/bin/
COPY --from=helm /helm/linux-amd64/helm ./usr/bin/
COPY --from=poetry /root/.poetry ./root/.poetry

# ===================================
FROM docker:stable-dind as app-base
# ===================================

ENV PYTHONUNBUFFERED=1

COPY --from=stage /stage/ /

# Symlink poetry to bin
RUN ln -s $HOME/.poetry/bin/poetry /usr/bin/poetry

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
        ca-certificates \
        git \
        make \
        openssl-dev \
        libffi-dev \
    && ln -sf python3 /usr/bin/python \
    && ln -s pip3 /usr/bin/pip \
    && poetry config settings.virtualenvs.create false \
	&& poetry install --no-dev --no-interaction \
	&& pip install docker-compose \
	&& apk del .build-deps \
	&& apk del .fetch-deps

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

# ===================================
FROM app-base AS development
# ===================================

RUN apk add --no-cache --virtual .build-deps \
        build-base \
        python3-dev \
    && poetry install \
    && apk del .build-deps

COPY . /app

# ===================================
FROM app-base AS production
# ===================================

COPY . /app
