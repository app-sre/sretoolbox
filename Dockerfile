# vi:set ft=dockerfile:
FROM registry.access.redhat.com/ubi10/python-314-minimal@sha256:6a3ac934913b426ccf9a9d8406084e47044ef8da88a6722a3acc60ac990595c3 AS test
COPY --from=ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d /uv /bin/uv
COPY LICENSE /licenses/

USER 0
RUN microdnf install -y make && microdnf clean all
USER 1001
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
