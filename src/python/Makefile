# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

# __author__="${FULL_NAME}"
# __copyright__="Copyright (c) 2017 OSIsoft, LLC"
# __license__="Apache 2.0"
# __version__="${VERSION}"

# FogLAMP build tasks (makefile)

USER := $(shell whoami)
OS := $(shell uname)
CODEDIR := ../src/python/foglamp

check-root:
ifeq ($(USER), root)
	@echo "INFO: Installing as root."
endif

help:
	@echo Targets:
	@echo "clean - remove all build, cache, test"
	@echo "clean-build - remove build artifacts"
	@echo "clean-doc - remove docs artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test artifacts"
	@echo "cov-report - generate html test coverage report and open it in browser"
	@echo "develop - install dev dependencies and FogLAMP using setup.py"
	@echo "doc - generate docs html"
	@echo "doc-build-test - run docs/check-sphinx tests"
	@echo "install - install production dependencies and FogLAMP using setup.py"
	@echo "install-dep - install dependencies using requirements.txt"
	@echo "install-dev-dep - install dependencies using requirements-dev.txt"
	@echo "install-doc-dep - install dependencies using requirements-doc.txt"
	@echo "install-test-dep - install dependencies using requirements-test.txt"
	@echo "install-tox - install tox dependency"
	@echo "lint - run python and js lint checks"
	@echo "lint-js - run ui/*.js files lint check only"
	@echo "lint-python - run python files lint check only"
	@echo "live-doc - generate docs and allow autobuild on change in source .rst files"
	@echo "py-test - run src/python/tests"
	@echo "test - run all tests (src/python/tests and docs/check-sphinx)"
	@echo "test-report - generate allure report for (src/python/tests and docs/check-sphinx) and open it in browser"

clean: clean-build clean-doc clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr ~/var
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-doc:
	rm -fr ../../docs/_build/
	rm -fr ../../docs/.cache/
	find ../../docs -name '__pycache__' -exec rm -fr {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -type f -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .cache
	rm -fr .tox
	rm -fr .coverage
	rm -fr htmlcov/
	rm -fr ../../allure/
	rm -f coverage.xml

cov-report:
ifeq ($(OS), Darwin)
	open htmlcov/index.html
endif
ifeq ($(OS), Linux)
	xdg-open htmlcov/index.html
endif

develop: install-dev-dep
	pip3 install -e . --user

doc: install-doc-dep
	make install
	cd ../../docs && sphinx-apidoc -fT -o ./source $(CODEDIR) && make html

doc-build-test: install-tox
	tox -e docs

install-dep: check-root
	pip3 install -r requirements.txt

install: install-dep
	python3 setup.py install

install-dev-dep: check-root
	pip3 install -r requirements-dev.txt --user

install-doc-dep: check-root
	pip3 install -r requirements-doc.txt --user

install-test-dep: check-root
	pip3 install -r requirements-test.txt --user

install-tox: check-root
	pip3 install tox --user

lint: lint-python lint-js

lint-js:
	@echo "-- TODO: add js lint | added here for example, to add later"

lint-python: install-test-dep
	rm -f pylint*.log
	pylint $(shell pwd) > pylint_$(shell date +%FT%T%Z).log || exit 0

live-doc: install-doc-dep
	make install
	cd ../../docs && sphinx-apidoc -fT -o ./source $(CODEDIR) && make livehtml

py-test: install-tox
	tox -e py35

test: py-test doc-build-test

test-report:
	cd ../../allure/ && allure generate . && allure report open

.PHONY: \
	help \
	clean \
	clean-build \
	clean-doc \
	clean-pyc \
	clean-test \
	cov-report \
	develop \
	doc \
	doc-build-test \
	install \
	install-dep \
	install-dev-dep \
	install-doc-dep \
	install-test-dep \
	install-tox \
	lint \
	lint-js \
	lint-python \
	live-doc \
	py-test \
	test \
	test-report
