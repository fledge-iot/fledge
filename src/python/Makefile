USER := $(shell whoami)

check-root:
ifeq ($(USER), root)
	@echo "WARNING: Installing as root should be avoided at all costs. Use a virtualenv"
endif

help:
	@echo "clean - remove all build, cache, test"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test artifacts"
	@echo "install-py-requirements - installing python dependencies using requirements.txt"
	@echo "install-dev-requirements - installing python dev dependencies using requirements_dev.txt"
	@echo "install-doc-requirements - installing sphinx doc dependencies using requirements_doc.txt"
	@echo "install-test-requirements - installing test dependencies using requirements_test.txt"
	@echo "create-env - create environment file if it doesn't exist (copy foglamp-env.example.yaml to foglamp-env.yaml)"
	@echo "test - run all (src/python/tests and docs/check_sphinx) tests"
	@echo "py-test - run src/python/tests"
	@echo "doc-build-test - run docs/check_sphinx tests"
	@echo "lint - run python and js lint checks"
	@echo "lint-python - run python files lint check only"
	@echo "lint-js - run ui/*.js files lint check only"
	@echo "doc - generate docs html"
	@echo "live-doc - generate docs and allow autobuild on change in source .rst files"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .cache
	rm -fr .tox

install-py-requirements: check-root
	@echo "-- Installing Python dependencies"
	pip install -r requirements.txt

install-dev-requirements: check-root
	@echo "-- Installing Python dev dependencies"
	pip install -r requirements_dev.txt

install-doc-requirements: check-root
	@echo "-- Installing Sphinx doc dependencies"
	pip install -r requirements_doc.txt

install-test-requirements: check-root
	@echo "-- Installing test dependencies"
	pip install -r requirements_test.txt

create-env:
	@echo "-- Creating environment file"
	[ -f foglamp/foglamp-env.yaml ] && echo "foglamp-env already exists" || cp foglamp/foglamp-env.example.yaml foglamp/foglamp-env.yaml

test: py-test doc-build-test

py-test:
	@echo "-- Executing python tests"
	pip install tox
	tox -e py35

doc-build-test:
	@echo "-- Executing sphinx doc builder tests"
	pip install tox
	tox -e docs

lint: lint-python lint-js

lint-python: install-test-requirements
	@echo "-- Linting Python files"
	rm -f pylint*.log
	pylint $(shell find . -iname "*.py" ! -path './venv*' ! -path './.tox*') > pylint_$(shell date +%FT%T%Z).log || exit 0

lint-js:
    @echo "-- TODO: add js lint | added here for example, to add later"

doc: install-doc-requirements
	@echo "-- Generate docs html"
	cd ../../docs && make html

live-doc: install-doc-requirements
	cd ../../docs && make livehtml

.PHONY: \
	help \
	clean \
	clean-build \
	clean-pyc \
	clean-test \
	install-py-requirements \
	install-dev-requirements \
	install-doc-requirements \
	install-test-requirements \
	create-env\
	lint \
	lint-python \
	lint-js \
	doc \
	live-doc \
	test \
	py-test \
	doc-build-test

