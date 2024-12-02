# These shell flags are REQUIRED for an early exit in case any program called by make errors
.SHELLFLAGS=-euo pipefail -c
SHELL := /bin/bash

all:
	@echo
	@echo "Targets:"
	@echo "develop:      Installs the sretoolbox package, its dependencies and its development dependencies."
	@echo "check:        Runs the style check, the code check and the tests."
	@echo "clean:        Removes the virtualenv and python artifacts."
	@echo

develop:
	uv sync --python 3.9

check:
	uv run ruff format --check
	uv run ruff check --no-fix
	uv run pytest -v --cov=sretoolbox --cov-report=term-missing tests/

clean:
	find . -type d \( -name "build" -o -name "dist" -o -name "*.egg-info" \) -exec rm -fr {} +
	find . \( -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" \) -exec rm -fr {} +
