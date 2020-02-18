#!/bin/bash

set -e

python3 -m pip install --user twine wheel
python3 setup.py bdist_wheel
twine upload dist/*
