# These shell flags are REQUIRED for an early exit in case any program called by make errors
.SHELLFLAGS=-euo pipefail -c
SHELL := /bin/bash

all:
	@echo
	@echo "Targets:"
	@echo "prepare:      Installs pipenv."
	@echo "install:      Installs the sretoolbox package and its dependencies."
	@echo "develop:      Installs the sretoolbox package, its dependencies and its development dependencies."
	@echo "check:        Runs the style check, the code check and the tests."
	@echo "clean:        Removes the virtualenv and python artifacts."
	@echo


prepare:
	pip install pipenv --user --upgrade

install: prepare
	pipenv install

develop: prepare
	pipenv install --dev

check:
	pipenv run flake8 sretoolbox
	pipenv run pylint sretoolbox
	pipenv run pipenv run pytest -v --cov=sretoolbox --cov-report=term-missing tests/

clean:
	pipenv --rm
	find . -type d \( -name "build" -o -name "dist" -o -name "*.egg-info" \) -exec rm -fr {} +
	find . \( -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" \) -exec rm -fr {} +
