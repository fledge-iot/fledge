# FOGLAMP_PRELUDE_BEGIN
# {{FOGLAMP_LICENSE_DESCRIPTION}}
# See: http://foglamp.readthedocs.io/
#
# Copyright (c) 2017 OSIsoft, LLC
# License: Apache 2.0
# FOGLAMP_PRELUDE_END
#
# __author__ = ${FULL_NAME}
# __version__ = ${VERSION}
#
# FogLAMP build tasks (makefile)

USER := $(shell whoami)

check-root:
ifeq ($(USER), root)
	@echo "WARNING: Installing as root should be avoided. Use a virtual environment."
	exit 1
endif

help:
	@echo "clean - remove all build, cache, test"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test artifacts"
	@echo "create-env - create environment file if it doesn't exist (copy foglamp-env.example.yaml to foglamp-env.yaml)"
	@echo "doc - generate docs html"
	@echo "doc-build-test - run docs/check_sphinx tests"
	@echo "install - install production dependencies and FogLAMP using setup.py"
	@echo "install-requirements - install dependencies using requirements.txt"
	@echo "install-all-requirements - install dependencies using requirements-all.txt"
	@echo "install-dev-requirements - install dependencies using requirements-dev.txt"
	@echo "install-lint-requirements - install dependencies using requirements-lint.txt"
	@echo "install-doc-requirements - install dependencies using requirements-doc.txt"
	@echo "install-test-requirements - install dependencies using requirements-test.txt"
	@echo "lint - run python and js lint checks"
	@echo "lint-js - run ui/*.js files lint check only"
	@echo "lint-python - run python files lint check only"
	@echo "live-doc - generate docs and allow autobuild on change in source .rst files"
	@echo "py-test - run src/python/tests"
	@echo "test - run all tests (src/python/tests and docs/check_sphinx)"

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
	find . -type f -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .cache
	rm -fr .tox

install-requirements: check-root
	pip install -r requirements.txt

install-all-requirements: check-root
	pip install -r requirements-all.txt

install-dev-requirements: check-root
	pip install -r requirements-dev.txt

install-doc-requirements: check-root
	pip install -r requirements-doc.txt

install-lint-requirements: check-root
	pip install -r requirements-lint.txt

install-test-requirements: check-root
	pip install -r requirements-test.txt

install: install-requirements
	pip install -e .

# TODO deleteme
create-env:
	[ -f foglamp/foglamp-env.yaml ] && echo "foglamp-env already exists" || cp foglamp/foglamp-env.example.yaml foglamp/foglamp-env.yaml
	
test: py-test doc-build-test

py-test: install-test-requirements
	tox -e py35

doc-build-test: install-doc-requirements
	tox -e docs

lint: 
	lint-python lint-js

lint-python: install-lint-requirements
	rm -f pylint*.log
	pylint $(shell find . -iname "*.py" ! -path './venv*' ! -path './.tox*') > pylint_$(shell date +%FT%T%Z).log || exit 0

lint-js:
  @echo "-- TODO: add js lint | added here for example, to add later"

doc: install-doc-requirements
	cd ../../docs && make html

live-doc: install-doc-requirements
	cd ../../docs && make livehtml

.PHONY: \
	help \
	clean \
	clean-build \
	clean-pyc \
	clean-test \
	install \
	install-requirements \
	install-all-requirements \
	install-dev-requirements \
	install-doc-requirements \
	install-lint-requirements \
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
