USER := $(shell whoami)

check-root:
ifeq ($(USER), root)
	@echo "WARNING: Installing as root should be avoided at all costs. Use a virtualenv."
endif

help:
	@echo "clean - remove all build, cache, test"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test artifacts"
	@echo "install-python-requirements - installing Python development dependencies using requirements.txt"
	@echo "copy-config - copy example configuration file"
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

install-python-requirements: check-root
	@echo "-- Installing Python development dependencies."
	pip install -r requirements.txt

copy-config:
	@echo "-- Copying configuration file."
	[ -f foglamp/foglamp-env.yaml ] && echo "foglamp-env already exists." || cp foglamp/foglamp-env.example.yaml foglamp/foglamp-env.yaml
	[ -f foglamp-config.yaml ] && echo "foglamp-config already exists." || cp foglamp-config.example.yaml foglamp-config.yaml

lint: lint-python lint-js

lint-python:
	@echo "-- Linting Python files."
	rm -f pylint*.log
	pylint $(shell find . -iname "*.py" ! -path './venv*' ! -path './.tox*') --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > pylint_$(shell date +%FT%T%Z).log || exit 0

lint-js:
    @echo "-- TODO: add js lint | added here for example, to add later"

doc:
	@echo "-- Generate docs html."
	cd ../../docs && make html

live-doc:
	cd ../../docs && make livehtml

.PHONY: \
	help \
	clean \
	clean-build \
	clean-pyc \
	clean-test \
	install-python-requirements \
	copy-config \
	lint \
	lint-python \
	lint-js \
	doc \
	live-doc
