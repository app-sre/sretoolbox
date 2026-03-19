# vi:set ft=dockerfile:
FROM registry.access.redhat.com/ubi9-minimal@sha256:f225a0f8eb7d258011e1f7c8b025dc7dd155d6ffc66c17cd203dcec88935b455 AS test
COPY --from=ghcr.io/astral-sh/uv:0.9.25@sha256:13e233d08517abdafac4ead26c16d881cd77504a2c40c38c905cf3a0d70131a6 /uv /bin/uv
COPY LICENSE /licenses/

RUN microdnf install -y make && microdnf clean all
WORKDIR /app

# Install build dependencies
COPY pyproject.toml uv.lock LICENSE README.md Makefile ./

# the source code
COPY sretoolbox ./sretoolbox
COPY --chown=1001:0 tests ./tests

# Run tests
RUN make check
USER 1001

#
# PyPI publish image
#
FROM test AS pypi
# Secrets are owned by root and are not readable by others :(
USER root
RUN --mount=type=secret,id=app-sre-pypi-credentials/token UV_PUBLISH_TOKEN=$(cat /run/secrets/app-sre-pypi-credentials/token) make pypi
USER 1001
