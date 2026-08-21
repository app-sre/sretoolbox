# vi:set ft=dockerfile:
FROM registry.access.redhat.com/ubi10/python-314-minimal@sha256:b03ba8137469b97fa0997a5770d3dfc9b13a0448603eafa181818022b205cf1e AS test
COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 /uv /bin/uv
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
