# vi:set ft=dockerfile:
FROM registry.access.redhat.com/ubi10/python-314-minimal@sha256:a7f537598b1a6737c56f463421f490cbc12a0f60ca64d87f0b91944b34ee03db AS test
COPY --from=ghcr.io/astral-sh/uv:0.12.15@sha256:62f8c047d0a0e9ece6b53fc63df902585a67a47a7f318ddec4a37db586edc8e3 /uv /bin/uv
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
