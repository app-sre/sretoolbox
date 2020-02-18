all:
	@echo
	@echo "Targets:"
	@echo "prepare:      Installs pipenv."
	@echo "install:      Installs the sretoolbox package and its dependencies."
	@echo "develop:      Installs the sretoolbox package, its dependencies and its development dependencies."
	@echo "check:        Runs the style check, the code check and the tests."
	@echo


prepare:
	pip install pipenv --upgrade

install: prepare
	pipenv install

develop: prepare
	pipenv install --dev

check:
	pipenv run flake8 sretoolbox
	pipenv run pylint sretoolbox
	pipenv run pipenv run pytest -v --cov=sretoolbox --cov-report=term-missing tests/
