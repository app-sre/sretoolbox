# vi:set ft=dockerfile:
FROM registry.redhat.io/ubi9/python-39@sha256:49f0e4711ec5f7358cdf3c89ef835a7dcccb6da3370e916fcdfddd392856c39a AS test
COPY --from=ghcr.io/astral-sh/uv:0.5.5@sha256:dc60491f42c9c7228fe2463f551af49a619ebcc9cbd10a470ced7ada63aa25d4 /uv /bin/uv

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

FROM test AS pypi
ARG TWINE_USERNAME
ARG TWINE_PASSWORD

RUN make pypi
