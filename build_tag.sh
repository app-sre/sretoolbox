#!/bin/bash

docker build -t sretoolbox -f Dockerfile \
    --target pypi \
    --build-arg TWINE_USERNAME \
    --build-arg TWINE_PASSWORD \
    .
