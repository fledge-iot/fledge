#!/bin/bash

set -e

# Usage:
   # ./build.sh
   # ./build.sh -h
   # ensure permission: chmod 700 build.sh

usage="$(basename "sh $0") [-h] [-t | --test] [--doc] -- Setup virtual env, install the requirements
where:
    -h  show this help text
    -t, --test runs tests
    -i, --install runs pip install -e .
    -u, --uninstall uninstalls the  package and remove installed scripts
    --doc generate docs html in docs/_build directory"

setup_and_run() {

    echo "--- installing virtualenv ---"
    # shall ignore if already installed
    pip3.5 install virtualenv

    # which python3.5
    python_path=$( which python3.5 )

    echo "--- setting the virtualenv using python_path; should be 3.5.2 found ${python_path} ---"

    virtualenv --python=$python_path venv/fogenv


    echo "--- installing requirements which were frozen using [pip freeze > requirements.txt]---"
    venv/fogenv/bin/pip install -r requirements.txt

    if [ "$option" == "TEST" ]
    then
        echo "run tests? will add tox.ini to run via tox"
        echo "until then, checking db config"

        # venv/fogenv/bin/pip install -e . # uncomment or run with -i first to test
        venv/fogenv/bin/python tests/db_config.py

    elif [ "$option" == "INSTALL" ]
    then
        venv/fogenv/bin/pip install -e .

    elif [ "$option" == "BUILD_DOC" ]
    then
        echo "Running make html in docs"
        cd ../../docs/
        make html
        cd ../src/python/

    elif [ "$option" == "UNINSTALL" ]
    then
        echo "This will remove the package"
        venv/fogenv/bin/pip uninstall FogLAMP <<< y
    fi

    # echo "--- removing virtualenv directory ---"
    # rm -rf venv/fogenv
}

option=''

if [ $# -gt 0 ]
  then
     for i in "$@"
     do
         case $i in

           -t|--test)
             option="TEST"
             ;;

            -i|--i)
             option="INSTALL"
             ;;

            -u|--uninstall)
             option="UNINSTALL"
             ;;

            --doc)
             option="BUILD_DOC"
             ;;

            *)
             echo "${usage}" # anything including -h :]
             break
             ;;
         esac
         setup_and_run
     done
  else
     setup_and_run
fi