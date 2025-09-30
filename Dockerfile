# vi:set ft=dockerfile:
FROM registry.access.redhat.com/ubi9/python-39@sha256:49f0e4711ec5f7358cdf3c89ef835a7dcccb6da3370e916fcdfddd392856c39a AS test
COPY --from=ghcr.io/astral-sh/uv:0.8.22@sha256:9874eb7afe5ca16c363fe80b294fe700e460df29a55532bbfea234a0f12eddb1 /uv /bin/uv
COPY LICENSE /licenses/

ENV \
    # use venv from ubi image
    UV_PROJECT_ENVIRONMENT=$APP_ROOT \
    # compile bytecode for faster startup
    UV_COMPILE_BYTECODE="true" \
    # disable uv cache. it doesn't make sense in a container
    UV_NO_CACHE=true

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --python /usr/bin/python3

# other project related files
COPY LICENSE README.md Makefile ./

# the source code
COPY sretoolbox ./sretoolbox
COPY --chown=1001:0 tests ./tests
RUN uv sync --frozen --no-editable

# Run tests
RUN make check

#
# PyPI publish image
#
FROM test AS pypi
# Secrets are owned by root and are not readable by others :(
USER root
RUN --mount=type=secret,id=app-sre-pypi-credentials/token UV_PUBLISH_TOKEN=$(cat /run/secrets/app-sre-pypi-credentials/token) make pypi
USER 1001
