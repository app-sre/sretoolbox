#!/bin/bash

docker build -t sretoolbox -f Dockerfile --target test .
