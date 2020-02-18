#!/bin/bash

IMAGE_TEST=sretoolbox

docker build -t ${IMAGE_TEST} -f Dockerfile.test .
docker run --rm ${IMAGE_TEST}
