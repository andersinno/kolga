#!/bin/sh

# A wrapper for docker to check that wait for docker daemon to spin up. See:
# https://gitlab.com/gitlab-org/gitlab-runner/-/issues/27300

wait_for_dockerd() {
    END=$(expr $(date +%s) + 30)  # Wait for 30s at most.
    while ! /usr/bin/docker info >/dev/null 2>&1; do
        if [ $(date +%s) -ge "$END" ]; then
            return 1
        fi
        sleep 1
    done
}

if ! wait_for_dockerd; then
    echo "Failed to connect Docker daemon!" >&2
    exit 1
fi

exec /usr/bin/docker "$@"
