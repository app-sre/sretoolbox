#!/bin/bash

docker build -t sretoolbox -f Dockerfile \
    --target pypi \
    --build-arg UV_PUBLISH_USERNAME="$TWINE_USERNAME" \
    --build-arg UV_PUBLISH_PASSWORD="$TWINE_PASSWORD" \
    .
