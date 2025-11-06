PYTEST_CMD = pytest -v --cov=sretoolbox --cov-report=term-missing tests/

all:
	@echo
	@echo "Targets:"
	@echo "develop:      Installs the sretoolbox package, its dependencies and its development dependencies."
	@echo "check:        Runs the style check, the code check and the tests."
	@echo "clean:        Removes the virtualenv and python artifacts."
	@echo

develop:
	uv sync

check:
	uv run ruff format --check
	uv run ruff check --no-fix
	uv run mypy
	uv run --python=3.10 $(PYTEST_CMD)
	uv run --python=3.11 $(PYTEST_CMD)
	uv run --python=3.12 $(PYTEST_CMD)
	uv run --python=3.13 $(PYTEST_CMD)
	uv run --python=3.14 $(PYTEST_CMD)

clean:
	find . -type d \( -name "build" -o -name "dist" -o -name "*.egg-info" \) -exec rm -fr {} +
	find . \( -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" \) -exec rm -fr {} +

pypi:
	uv build --sdist --wheel --out-dir dist
	uv publish || true
