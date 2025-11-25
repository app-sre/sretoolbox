# vi:set ft=dockerfile:
FROM registry.access.redhat.com/ubi9-minimal@sha256:61d5ad475048c2e655cd46d0a55dfeaec182cc3faa6348cb85989a7c9e196483 AS test
COPY --from=ghcr.io/astral-sh/uv:0.9.12@sha256:0eaa66c625730a3b13eb0b7bfbe085ed924b5dca6240b6f0632b4256cfb53f31 /uv /bin/uv
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
